"""Coverage of real questions, typed graph provenance and optional synthesis."""
import json
from pathlib import Path

import pytest
import requests

from test_agents_project import web_app, browser, chat_request, ROOT
from mvc.controllers.agents_controller import get_agents_model
from mvc.models.assistant_synthesis import AssistantSynthesis

CASES=json.loads((ROOT/'tests/diabetes_chat_cases.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('question,expected',CASES)
def test_expanded_questions_have_relevant_sourced_answers(browser,question,expected):
    task=chat_request(browser,question)['task']
    assert task['outcome']=='ANSWERED'
    assert task['evidence'][0]['doc_id']==expected
    assert task['blocks'] and any(f['evidence_id']==expected for f in task['graph'])
    assert not task['prediction']
    assert all(b['evidence_ids'] for b in task['blocks'])


def test_graph_has_distinct_concepts_aliases_and_source_provenance(browser,web_app):
    with web_app.app_context():
        model=get_agents_model()
        stats=model.dialogue.statistics()
        assert stats['documents']==174 and stats['sources']>=160
        assert stats['clinical_entities']>150 and stats['clinical_relations']>120
        graph=model.dialogue.graph
        assert stats['nodes']==len(graph)
        assert all(data['evidence_id'] in model.dialogue.documents for _,_,data in graph.edges(data=True))
        for _,_,_,did in model.dialogue.facts:
            assert graph.has_edge(did,model.dialogue.documents[did]['source_url'])
        assert len(model.knowledge.documents)==10  # frozen experiment stays intact


@pytest.fixture
def synthesis(tmp_path,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','unit-test-secret-do-not-expose')
    monkeypatch.setenv('ASSISTANT_GEMINI_MODEL','gemini-3.5-flash-lite')
    return AssistantSynthesis(tmp_path,enabled=True)


@pytest.fixture
def evidence():
    return [dict(doc_id='K05',title='Alcohol and diabetes',content='Alcohol can cause low blood glucose and interact with diabetes medicines.')]


def valid_response(evidence):
    return dict(blocks=[dict(text='Rượu bia có thể gây hạ đường huyết; cần trao đổi với bác sĩ.',
        evidence_ids=['K05'],support_quotes=[dict(doc_id='K05',quote=evidence[0]['content'])])])


def test_external_request_uses_header_and_only_public_context(synthesis,evidence,monkeypatch):
    captured={}
    def post(url,**kwargs):
        captured.update(url=url,**kwargs)
        class Response:
            status_code=200
            content=b'bounded'
            def json(self):
                return {'candidates':[{'content':{'parts':[{'text':json.dumps(valid_response(evidence))}]}}]}
        return Response()
    monkeypatch.setattr(requests,'post',post)
    result=synthesis.compose('Can I drink alcohol?',evidence)
    assert result['status']=='completed'
    assert 'key=' not in captured['url']
    assert captured['headers']['x-goog-api-key']=='unit-test-secret-do-not-expose'
    assert 'unit-test-secret' not in json.dumps(result)
    body=json.dumps(captured['json'])
    assert 'owner_id' not in body and 'profile' not in body and 'source_url' not in body
    assert captured['timeout']==(3,12) and captured['allow_redirects'] is False


@pytest.mark.parametrize('failure',['timeout','quota','bad_json','unknown_source','unsupported_quote'])
def test_external_failure_keeps_trusted_local_answer_and_cools_down(synthesis,evidence,monkeypatch,failure):
    calls=[]
    def post(*args,**kwargs):
        calls.append(1)
        if failure=='timeout':raise requests.Timeout('sensitive provider detail')
        class Response:
            status_code=429 if failure=='quota' else 200
            content=b'bounded'
            def json(self):
                if failure=='bad_json':raise ValueError('sensitive provider detail')
                value=valid_response(evidence)
                if failure=='unknown_source':value['blocks'][0]['evidence_ids']=['unknown']
                if failure=='unsupported_quote':value['blocks'][0]['support_quotes'][0]['quote']='not in any source'
                return {'candidates':[{'content':{'parts':[{'text':json.dumps(value)}]}}]}
        return Response()
    monkeypatch.setattr(requests,'post',post)
    result=synthesis.compose('question',evidence)
    assert result['status']=='fallback' and 'blocks' not in result
    assert 'sensitive' not in json.dumps(result)
    assert synthesis.compose('question',evidence)['status']=='fallback' and len(calls)==1


def test_synthesis_not_called_without_evidence(synthesis,monkeypatch):
    monkeypatch.setattr(requests,'post',lambda *a,**kw:pytest.fail('No source must mean no network generation'))
    assert synthesis.compose('unrelated question',[]) is None


def test_chat_persists_assisted_answer_but_falls_back_without_losing_sources(browser,web_app,monkeypatch):
    with web_app.app_context():
        model=get_agents_model()
        def compose(question,evidence):
            return dict(status='completed',duration_ms=10,blocks=[dict(text='Nội dung tổng hợp có nguồn.',evidence_ids=[evidence[0]['doc_id']])])
        monkeypatch.setattr(model.synthesis,'compose',compose)
    first=chat_request(browser,'Tiểu đường uống rượu được không?')
    task=first['task']
    assert task['answer_blocks'] and task['blocks'] and task['evidence'][0]['doc_id']=='K05'
    history=browser[0].get('/api/v1/assistant/conversations/'+first['conversation_id']).get_json()['tasks']
    assert history[0]['answer_blocks']==task['answer_blocks']
    monkeypatch.setattr(model.synthesis,'compose',lambda *a:dict(status='fallback',duration_ms=2))
    next_task=chat_request(browser,'Tiểu đường tuýp 2 là gì?')['task']
    assert next_task['outcome']=='ANSWERED' and next_task['blocks'] and 'answer_blocks' not in next_task


def test_answer_validation_rejects_dosing_but_accepts_glucose_units(evidence):
    value=valid_response(evidence)
    value['blocks'][0]['text']='Hãy dùng metformin 500 mg mỗi ngày.'
    with pytest.raises(ValueError):AssistantSynthesis.validate(value,evidence)
    value['blocks'][0]['text']='Đường huyết lúc đói 126 mg/dL cần được bác sĩ đánh giá.'
    assert AssistantSynthesis.validate(value,evidence)
