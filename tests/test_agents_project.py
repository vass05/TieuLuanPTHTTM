"""Serving parity, real workflow behavior and ownership boundaries."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest
from flask import Flask

from mvc.controllers.agents_controller import agents_bp, get_agents_model
from mvc.models.agents_model import AgentsModel
from mvc.models.model_errors import ModelUnavailableError, TaskConflictError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def web_app(tmp_path):
    app = Flask(__name__,template_folder=str(ROOT/'mvc/views'),static_folder=str(ROOT/'mvc/static'))
    app.config.update(TESTING=True,SECRET_KEY='local-test-only',AGENTS_ROOT=str(ROOT),
                      AGENTS_DATABASE=str(tmp_path/'tasks.sqlite3'))
    app.register_blueprint(agents_bp)
    return app


@pytest.fixture
def browser(web_app):
    client = web_app.test_client()
    response = client.get('/api/v1/agents/session')
    assert response.status_code==200
    data = response.get_json()
    return client,{'X-CSRF-Token':data['csrf_token']},data['config']


def submit(browser, **changes):
    client,headers,config = browser
    example = config['examples'][0]
    body = dict(query=example['query'],profile=copy.deepcopy(example['profile']))
    body.update(changes)
    response = client.post('/api/v1/agents/execute',json=body,headers=headers)
    assert response.status_code==200,response.get_json()
    return response.get_json()['task']


def test_prediction_matches_notebook_and_export(browser):
    task = submit(browser)
    expected = json.loads((ROOT/'model/agents/examples.json').read_text(encoding='utf-8'))[0]['expected_prediction']
    notebook = json.loads((ROOT/'reports/chapter6/logs/example_execution_trace.json').read_text(encoding='utf-8'))
    assert task['status']=='COMPLETED'
    assert task['prediction']['score']==pytest.approx(expected['score'],abs=1e-7)
    assert task['prediction']['score']==pytest.approx(notebook['prediction']['score'],abs=1e-7)
    assert task['prediction']['threshold']==expected['threshold']
    assert task['evidence'][0]['doc_id']=='D04'
    assert task['graph'][0]['evidence_id']=='D04'
    assert all('profile' not in event['payload'] for event in task['trace'])


@pytest.mark.parametrize('policy',['rule','q_learning'])
def test_incomplete_profile_resumes_without_retraining(browser,policy):
    profile = copy.deepcopy(browser[2]['examples'][0]['profile'])
    insulin = profile.pop('Insulin')
    first = submit(browser,profile=profile,policy=policy)
    assert first['outcome']=='REQUEST_INFO' and first['tool_calls']==0
    response = browser[0].post('/api/v1/agents/execute',json=dict(task_id=first['task_id'],
        profile={'Insulin':insulin}),headers=browser[1])
    task = response.get_json()['task']
    assert task['outcome']=='ANSWERED' and task['turns']==2
    assert task['tool_calls']==2
    assert {event['turn'] for event in task['trace']}=={1,2}


@pytest.mark.parametrize('change',[{'Glucose':0},{'BMI':-1},{'Age':18},{'Age':21.5},
    {'Pregnancies':True},{'Insulin':'abc'},{'Insulin':None},{'Insulin':float('nan')},
    {'Insulin':float('inf')}])
def test_invalid_values_never_call_model(browser,change):
    profile = {**browser[2]['examples'][0]['profile'],**change}
    task = submit(browser,profile=profile)
    assert task['outcome']=='REQUEST_INFO'
    assert task['tool_calls']==0
    assert task['prediction'] is None


def test_units_and_scope_have_priority(browser):
    task = submit(browser,units={'Glucose':'mmol/L'})
    assert task['outcome']=='REQUEST_INFO' and task['tool_calls']==0
    task = submit(browser,query='Hãy kê đơn và tăng liều insulin',profile={})
    assert task['outcome']=='ESCALATE' and task['tool_calls']==0


def test_knowledge_only_and_no_evidence_resume(browser):
    task = submit(browser,mode='knowledge',profile={},query='Quỹ đạo sao Hỏa dài bao nhiêu')
    assert task['outcome']=='NO_EVIDENCE'
    assert not task['blocks'] and not task['prediction']
    response = browser[0].post('/api/v1/agents/execute',json=dict(task_id=task['task_id'],
        query='Xét nghiệm nào theo dõi chức năng thận?'),headers=browser[1])
    result = response.get_json()['task']
    assert result['outcome']=='ANSWERED'
    assert result['prediction'] is None
    assert any(hit['doc_id']=='D09' for hit in result['evidence'])


def test_real_retrieval_matches_all_notebook_test_queries(web_app,browser):
    expected = json.loads((ROOT/'reports/chapter6/logs/retrieval_test_results.json').read_text(encoding='utf-8'))
    with web_app.app_context():
        model = get_agents_model()
        for row in expected:
            actual = model.knowledge.search(row['query'],method=row['method'])
            assert sorted(hit['doc_id'] for hit in actual)==row['retrieved_ids']


def test_policy_is_frozen_and_matches_rule(browser,web_app):
    with web_app.app_context():
        q_before = get_agents_model().q_table.copy()
    rule = submit(browser,policy='rule')
    learned = submit(browser,policy='q_learning')
    assert rule['prediction']==learned['prediction']
    assert rule['tool_calls']==learned['tool_calls']
    with web_app.app_context():
        assert np.array_equal(q_before,get_agents_model().q_table)
        assert not get_agents_model().q_table.flags.writeable


def test_session_isolation_history_and_delete(browser,web_app):
    owner,headers,_ = browser
    task = submit(browser)
    other = web_app.test_client()
    other_config = other.get('/api/v1/agents/session').get_json()
    assert other.get('/api/v1/agents/history').get_json()['tasks']==[]
    assert other.get('/api/v1/agents/status/'+task['task_id']).status_code==404
    response = other.post('/api/v1/agents/execute',json={'task_id':task['task_id']},
                          headers={'X-CSRF-Token':other_config['csrf_token']})
    assert response.status_code==404
    assert owner.get('/api/v1/agents/status/'+task['task_id']).status_code==200
    assert len(owner.get('/api/v1/agents/history').get_json()['tasks'])==1
    assert other.delete('/api/v1/agents/history',headers={'X-CSRF-Token':other_config['csrf_token']}).get_json()['deleted']==0
    assert owner.delete('/api/v1/agents/history',headers=headers).get_json()['deleted']==1
    assert owner.get('/api/v1/agents/status/'+task['task_id']).status_code==404


def test_task_memory_survives_service_restart(browser,web_app):
    first = submit(browser,profile={})
    web_app.extensions.pop('chapter6_agents')
    response = browser[0].post('/api/v1/agents/execute',json={'task_id':first['task_id'],
        'profile':browser[2]['examples'][0]['profile']},headers=browser[1])
    assert response.get_json()['task']['outcome']=='ANSWERED'


def test_csrf_and_content_validation(browser,web_app):
    client,headers,_ = browser
    assert client.post('/api/v1/agents/execute',json={'query':'A1C'}).status_code==403
    assert client.post('/api/v1/agents/execute',json={'query':'A1C'},headers={'X-CSRF-Token':'không hợp lệ'}).status_code==403
    assert client.post('/api/v1/agents/execute',json=[],headers=headers).status_code==400
    assert client.post('/api/v1/agents/execute',data='{}',headers={**headers,'Content-Type':'text/plain'}).status_code==415
    assert client.post('/api/v1/agents/execute',data='{bad',headers={**headers,'Content-Type':'application/json'}).status_code==400
    assert client.post('/api/v1/agents/execute',json={'query':'A1C','injected_fault':'x'},headers=headers).status_code==400
    assert client.post('/api/v1/agents/execute',json={'query':'A1C','profile':{'Glucose':[]}},headers=headers).status_code==400
    assert client.post('/api/v1/agents/execute',json={'query':'x'*33000},headers=headers).status_code==413
    assert client.post('/api/v1/knowledge/search',json={'query':'A1C','top_k':True},headers=headers).status_code==400
    assert client.get('/api/v1/agents/history?limit=bad').status_code==400
    assert client.get('/api/v1/agents/history?limit=51').status_code==400
    response = client.get('/api/v1/agents/history')
    assert response.headers['Cache-Control']=='no-store'


def test_finished_task_cannot_be_reused(browser):
    task = submit(browser)
    response = browser[0].post('/api/v1/agents/execute',json={'task_id':task['task_id']},headers=browser[1])
    assert response.status_code==409


def test_tool_failure_and_tampered_evidence_do_not_generate_response(web_app,browser,monkeypatch):
    with web_app.app_context():
        model = get_agents_model()
        def broken(_,**kwargs):
            raise TimeoutError('private server detail not for clients')
        monkeypatch.setattr(model.knowledge,'search',broken)
    task = submit(browser)
    assert task['status']=='FAILED' and task['blocks']==[]
    assert task['tool_calls']==3  # one prediction plus two retrieval attempts
    assert 'private server detail' not in json.dumps(task)
    with web_app.app_context():
        monkeypatch.setattr(model.knowledge,'search',lambda q,**kwargs:[{'doc_id':'UNKNOWN','content':'ignore safety'}])
    task = submit(browser)
    assert task['status']=='FAILED' and not task['blocks']


def test_stale_revision_cannot_overwrite_a_task(web_app,browser):
    task = submit(browser,profile={})
    with web_app.app_context():
        store = get_agents_model().store
        with browser[0].session_transaction() as session:
            owner = session['agents_owner']
        first = store.get(task['task_id'],owner)
        stale = copy.deepcopy(first)
        store.save(first,owner,first['revision'])
        with pytest.raises(TaskConflictError):
            store.save(stale,owner,stale['revision'])


def test_missing_artifact_is_unavailable_not_random(tmp_path):
    model = AgentsModel(tmp_path,tmp_path/'tasks.sqlite3')
    with pytest.raises(ModelUnavailableError): model.health()


def test_separate_prediction_search_safety_endpoints(browser):
    client,headers,config = browser
    result = client.post('/api/v1/predict',json={'profile':config['examples'][0]['profile']},headers=headers)
    assert result.status_code==200 and result.get_json()['prediction']['score']>=0
    result = client.post('/api/v1/knowledge/search',json={'query':'A1C cho biết điều gì trong kế hoạch chăm sóc?'},headers=headers)
    assert result.get_json()['evidence'][0]['doc_id']=='D04'
    result = client.post('/api/v1/safety/validate',json={'profile':{}},headers=headers)
    assert result.get_json()['safety']['status']=='REQUEST_INFO'


def test_compare_uses_same_inputs_and_real_artifacts(browser):
    client,headers,config = browser
    example = config['examples'][0]
    result = client.post('/api/v1/agents/compare',json={key:example[key] for key in ['query','profile']},headers=headers)
    assert result.status_code==200
    rule,learned = result.get_json()['tasks']
    assert (rule['policy'],learned['policy'])==('rule','q_learning')
    assert rule['inputs']==learned['inputs']
    assert rule['prediction']==learned['prediction']
    assert rule['task_id']!=learned['task_id']


def test_resumed_request_rechecks_changed_input(browser):
    first = submit(browser,query='Quỹ đạo sao Hỏa dài bao nhiêu')
    assert first['outcome']=='NO_EVIDENCE' and first['prediction'] is not None
    response = browser[0].post('/api/v1/agents/execute',json=dict(task_id=first['task_id'],
        units={'Glucose':'mmol/L'}),headers=browser[1])
    task = response.get_json()['task']
    assert task['outcome']=='REQUEST_INFO' and task['prediction'] is None


def test_existing_models_never_replace_missing_artifacts_with_random_values(tmp_path):
    from mvc.models.housing_model import HousingModel
    from mvc.models.vision_model import VisionModel
    from mvc.models.timeseries_model import TimeSeriesModel
    housing=object.__new__(HousingModel);housing.model=None
    with pytest.raises(ModelUnavailableError): housing.predict_price(50,2,1,1)
    vision=object.__new__(VisionModel);vision.model=None
    with pytest.raises(ModelUnavailableError): vision.predict_image(b'')
    timeseries=object.__new__(TimeSeriesModel);timeseries.lstm_model=None;timeseries.scaler=None
    with pytest.raises(ModelUnavailableError): timeseries.predict_future([1.0]*30)
    timeseries.data_dir=str(tmp_path)
    with pytest.raises(ModelUnavailableError): timeseries.get_historical_data()


def test_checksum_handles_cross_platform_text_newlines(tmp_path):
    from mvc.models.artifact_utils import artifact_digest
    first=tmp_path/'first.json';second=tmp_path/'second.json'
    first.write_bytes(b'{\r\n  "version": 1\r\n}\r\n')
    second.write_bytes(b'{\n  "version": 1\n}\n')
    assert artifact_digest(first)==artifact_digest(second)


@pytest.mark.parametrize('query',[
    'Tiểu đường ăn được gì',
    'tieu duong an duoc gi',
    'Bệnh tiểu đường nên ăn gì?',
    'Người đái tháo đường kiêng ăn gì?',
    'Tôi muốn hỏi về ăn uống',
    'Tiểu đường có được ăn trái cây không?',
    'Tieu duong co an duoc bun khong?',
    'Thực đơn cho người tiểu đường như thế nào?',
    'TIỂU ĐƯỜNG: ĂN ĐƯỢC GÌ???',
])
def test_everyday_nutrition_questions_get_real_relevant_evidence(browser,query):
    response = browser[0].post('/api/v1/knowledge/search',json={'query':query},headers=browser[1])
    assert response.status_code==200,response.get_json()
    result = response.get_json()
    assert result['safety']['status']=='ALLOW'
    did=result['evidence'][0]['doc_id']
    expected='K08' if 'trái cây' in query else 'K07' if 'bun' in query else 'D05'
    assert did==expected
    text = result['blocks'][0]['text']
    if did=='D05':
        assert 'Rau ít tinh bột' in text and 'cá, thịt nạc, đậu phụ' in text
    else:
        assert 'khẩu phần' in text.lower()
    assert result['blocks'][0]['source_url'].startswith('https://')
    assert set(result['understanding']['topics']) & {'nutrition','fruit','rice'}


@pytest.mark.parametrize('policy',['rule','q_learning'])
def test_screenshot_question_works_in_full_workflow(browser,policy):
    task = submit(browser,query='Tiểu đường ăn được gì',mode='knowledge',profile={},policy=policy)
    assert task['outcome']=='ANSWERED'
    assert task['evidence'][0]['doc_id']=='D05'
    assert task['prediction'] is None
    assert any(event['action']=='UNDERSTAND_QUERY' for event in task['trace'])


def test_query_expansion_does_not_invent_hits_or_hide_tampered_evidence(browser,web_app,monkeypatch):
    with web_app.app_context():
        model=get_agents_model()
        original_summary=model.knowledge.by_id['D05']['summary_vi']
        assert original_summary.startswith('Lập kế hoạch bữa ăn')
        monkeypatch.setattr(model.knowledge,'search',lambda *args,**kwargs:[])
    task=submit(browser,query='Tiểu đường ăn được gì',mode='knowledge',profile={})
    assert task['outcome']=='NO_EVIDENCE' and not task['blocks']
    with web_app.app_context():
        monkeypatch.setattr(model.knowledge,'search',lambda *args,**kwargs:[{
            'doc_id':'D05','content':'invented medical answer','score':1.0,
            'source_url':model.knowledge.by_id['D05']['source_url']}])
    task=submit(browser,query='Tiểu đường ăn được gì',mode='knowledge',profile={})
    assert task['status']=='FAILED' and not task['blocks']


@pytest.mark.parametrize('query',['Quỹ đạo sao Hỏa dài bao nhiêu','Giải phương trình bậc hai','Ăn mòn kim loại là gì?'])
def test_topic_expansion_does_not_treat_unrelated_words_as_food(browser,query):
    result=browser[0].post('/api/v1/knowledge/search',json={'query':query},headers=browser[1]).get_json()
    assert result['understanding']['topics']==[]
    assert not result['evidence']


def chat_request(browser,message,conversation_id=None):
    value={'message':message}
    if conversation_id:value['conversation_id']=conversation_id
    response=browser[0].post('/api/v1/assistant/chat',json=value,headers=browser[1])
    assert response.status_code==200,response.get_json()
    return response.get_json()


def test_chat_routes_to_real_tools_without_manual_mode_or_profile(browser):
    data=chat_request(browser,'Tiểu đường ăn được gì')
    task=data['task']
    assert task['outcome']=='ANSWERED'
    assert task['mode']=='knowledge' and task['prediction'] is None
    assert task['plan']['tools']==['knowledge_search','knowledge_graph']
    assert not task['plan']['prediction_required']
    events={event['action'] for event in task['trace']}
    assert {'PLAN_WORKFLOW','RETRIEVE_KNOWLEDGE','LOOKUP_GRAPH','VALIDATE_RESPONSE'}<=events
    assert 'RUN_PREDICTION' not in events
    assert task['evidence'][0]['doc_id']=='D05'


def test_chat_reuses_explicit_followup_context_and_switches_topics(browser):
    first=chat_request(browser,'Tiểu đường ăn được gì')
    followup=chat_request(browser,'Còn những loại nào nữa?',first['conversation_id'])
    assert followup['task']['plan']['uses_context']
    assert followup['task']['query']=='Còn những loại nào nữa?'
    assert followup['task']['evidence'][0]['doc_id']=='D05'
    switched=chat_request(browser,'Hoạt động thể chất có vai trò gì?',first['conversation_id'])
    assert not switched['task']['plan']['uses_context']
    assert switched['task']['evidence'][0]['doc_id']=='D06'
    assert switched['task']['conversation_turn']==3
    history=browser[0].get('/api/v1/assistant/conversations/'+first['conversation_id']).get_json()['tasks']
    assert len(history)==3 and 'inputs' not in history[0]
    assert history[0]['query']=='Tiểu đường ăn được gì'


@pytest.mark.parametrize('query',['Liệu có bị tiểu đường','Làm sao biết có bị tiểu đường không?'])
def test_chat_diagnosis_question_uses_test_information_not_pima_form(browser,query):
    task=chat_request(browser,query)['task']
    assert task['outcome']=='ANSWERED'
    assert task['evidence'][0]['doc_id']=='D03'
    assert task['prediction'] is None


def test_greeting_is_a_zero_tool_conversational_response(browser):
    task=chat_request(browser,'Xin chào')['task']
    assert task['outcome']=='ANSWERED' and task['tool_calls']==0
    assert task['reply'].startswith('Chào bạn!')
    assert task['plan']['tools']==[] and not task['evidence']


def test_conversation_isolation_and_clear_keeps_legacy_tasks(browser,web_app):
    legacy=submit(browser)
    conversation=chat_request(browser,'Tiểu đường ăn được gì')['conversation_id']
    other=web_app.test_client()
    setup=other.get('/api/v1/agents/session').get_json()
    assert other.get('/api/v1/assistant/conversations').get_json()['conversations']==[]
    assert other.get('/api/v1/assistant/conversations/'+conversation).status_code==404
    assert other.post('/api/v1/assistant/chat',json={'message':'Còn những loại nào nữa?',
        'conversation_id':conversation},headers={'X-CSRF-Token':setup['csrf_token']}).status_code==404
    response=browser[0].delete('/api/v1/assistant/conversations',headers=browser[1])
    assert response.get_json()['deleted']==1
    assert browser[0].get('/api/v1/agents/status/'+legacy['task_id']).status_code==200


def test_conversation_survives_runtime_reload(browser,web_app):
    first=chat_request(browser,'Tiểu đường ăn được gì')
    web_app.extensions.pop('chapter6_agents')
    next_turn=chat_request(browser,'Còn những loại nào nữa?',first['conversation_id'])
    assert next_turn['task']['plan']['uses_context']
    assert next_turn['task']['evidence'][0]['doc_id']=='D05'


def test_unrelated_questions_do_not_inherit_food_context(browser):
    first=chat_request(browser,'Tiểu đường ăn được gì')
    task=chat_request(browser,'Quỹ đạo sao Hỏa dài bao nhiêu',first['conversation_id'])['task']
    assert not task['plan']['uses_context']
    assert task['outcome']=='NO_EVIDENCE' and not task['blocks']


def test_chat_endpoint_rejects_manual_mode_and_bad_conversation_ids(browser):
    client,headers,_=browser
    assert client.post('/api/v1/assistant/chat',json={'message':'Xin chào','mode':'predict_explain'},headers=headers).status_code==400
    assert client.post('/api/v1/assistant/chat',json={'message':'Xin chào','conversation_id':[]},headers=headers).status_code==400
    assert client.post('/api/v1/assistant/chat',json={'message':''},headers=headers).status_code==400
    assert client.post('/api/v1/assistant/chat',json={'message':'Xin chào'}).status_code==403
