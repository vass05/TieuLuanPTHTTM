"""Vietnamese source provenance, citations and compatibility with local serving."""
import json
import re

import pytest

from test_agents_project import ROOT, browser, chat_request, web_app
from mvc.controllers.agents_controller import get_agents_model
from mvc.models.diabetes_dialogue import load_extended_documents

CORPUS = ROOT / 'knowledge/diabetes_vietnam.json'
CASES = [
    ('Theo Bộ Y tế, đái tháo đường là gì?', 'V01'),
    ('khai niem dai thao duong bo y te', 'V01'),
    ('Yếu tố nguy cơ theo Bộ Y tế gồm những gì?', 'V02'),
    ('nguy co mac tieu duong theo bo y te', 'V02'),
    ('Ăn uống phòng tiểu đường theo Bộ Y tế như thế nào?', 'V03'),
    ('dinh duong hop ly de phong benh dai thao duong', 'V03'),
    ('Bộ Y tế vận động thể lực phòng bệnh như thế nào?', 'V04'),
    ('van dong phong benh theo bo y te', 'V04'),
    ('Nguy cơ hạ đường huyết theo Bộ Y tế là gì?', 'V05'),
    ('bo y te ha duong huyet', 'V05'),
    ('Dinh dưỡng theo Bạch Mai nên chú ý gì?', 'V06'),
    ('gao xat doi cho nguoi tieu duong', 'V06'),
]


@pytest.mark.parametrize('question,expected', CASES)
def test_vietnamese_sources_are_retrieved_and_cited(browser, question, expected):
    task = chat_request(browser, question)['task']
    assert task['outcome'] == 'ANSWERED'
    assert task['evidence'][0]['doc_id'] == expected
    document = next(doc for doc in load_extended_documents(CORPUS) if doc['doc_id'] == expected)
    assert task['evidence'][0]['source_url'] == document['source_url']
    assert task['evidence'][0]['publisher'] == document['publisher']
    assert task['blocks'] and all(block['evidence_ids'] for block in task['blocks'])
    assert any(fact['evidence_id'] == expected for fact in task['graph'])
    assert task['prediction'] is None


def test_vietnamese_documents_have_checked_source_provenance():
    documents = load_extended_documents(CORPUS)
    assert len(documents) == 6
    assert len({doc['doc_id'] for doc in documents}) == 6
    assert len({doc['source_url'] for doc in documents}) == 6
    assert {doc['publisher'] for doc in documents} == {
        'Cục Quản lý Khám, chữa bệnh – Bộ Y tế', 'Bệnh viện Bạch Mai'}
    for doc in documents:
        assert doc['source_country'] == 'VN' and doc['source_language'] == 'vi'
        assert doc['retrieved_on'] == doc['reviewed_on'] == '2026-11-06'
        assert doc['http_status'] == 200 and re.fullmatch(r'[0-9a-f]{64}', doc['source_sha256'])
        assert 1 <= sum(len(quote.split()) for quote in doc['support_quotes']) <= 16
        assert 35 <= len(doc['summary_vi'].split()) <= 125


@pytest.mark.parametrize('url', [
    'http://daithaoduong.kcb.vn/dai-thao-duong-la-gi',
    'https://daithaoduong.kcb.vn.untrusted.example/dai-thao-duong-la-gi',
    'https://unreviewed-hospital.vn/article',
])
def test_vietnamese_sources_do_not_allow_arbitrary_hosts_or_http(tmp_path, url):
    data = json.loads(CORPUS.read_text(encoding='utf-8'))
    data['documents'][0]['source_url'] = url
    path = tmp_path / 'invalid-source.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='Invalid knowledge source'):
        load_extended_documents(path)


def test_health_and_graph_include_vietnamese_sources(browser, web_app):
    health = browser[0].get('/api/v1/health').get_json()
    assert health['documents'] == 174
    assert health['knowledge_graph']['sources'] == 169
    with web_app.app_context():
        model = get_agents_model()
        assert len(model.knowledge.documents) == 10
        for doc in load_extended_documents(CORPUS):
            edge = model.dialogue.graph.get_edge_data(doc['doc_id'], doc['source_url'])
            assert any(data['evidence_id'] == doc['doc_id'] for data in edge.values())
