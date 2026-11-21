"""Exercise real Neo4j evidence through the assistant's public routes."""

import os
import json
from collections import Counter

import pytest

from test_agents_project import ROOT, web_app  # noqa: F401
from mvc.controllers.agents_controller import get_agents_model


@pytest.mark.skipif(os.getenv('TEST_DIABETES_NEO4J') != '1',
                    reason='Requires an imported Neo4j test instance')
def test_neo4j_pdf_and_web_evidence(web_app):
    web_app.config['DIABETES_KB_BACKEND'] = 'neo4j'
    with web_app.test_client() as client:
        session = client.get('/api/v1/agents/session').get_json()
        headers = {'X-CSRF-Token': session['csrf_token']}
        health = client.get('/api/v1/health').get_json()
        assert health['knowledge_backend']['name'] == 'neo4j'
        assert health['knowledge_backend']['sources'] == health['knowledge_graph']['sources']

        cases = [('PDF Bộ Y tế võng mạc', 'P01', 9),
                 ('Dinh dưỡng theo Bạch Mai nên chú ý gì?', 'V06', None),
                 ('A1C cho biết điều gì trong kế hoạch chăm sóc?', 'D04', None),
                 ('PDF Taking Medicines', 'P2AED01C4A1B0', 1)]
        for question, doc_id, page in cases:
            response = client.post('/api/v1/assistant/chat', headers=headers, json={'message': question})
            assert response.status_code == 200
            task = response.get_json()['task']
            assert task['outcome'] == 'ANSWERED', task['reasons']
            assert task['knowledge_backend'] == 'neo4j'
            evidence = task['evidence'][0]
            assert evidence['doc_id'] == doc_id
            assert evidence.get('page') == page
            assert evidence['kb_version'] == health['knowledge_backend']['version']
            assert any(fact['evidence_id'] == doc_id for fact in task['graph'])
            assert any(doc_id in block['evidence_ids'] for block in task['blocks'])
            trace = next(e for e in task['trace'] if e['action'] == 'RETRIEVE_KNOWLEDGE')
            assert trace['payload']['query_id'] == 'retrieve_evidence_v1'


def test_pdf_page_and_source_are_exposed_in_local_mode(web_app):
    with web_app.test_client() as client:
        session = client.get('/api/v1/agents/session').get_json()
        assert 'kcb.vn' in session['config']['source_hosts']
        headers = {'X-CSRF-Token': session['csrf_token']}
        response = client.post('/api/v1/assistant/chat', headers=headers,
                               json={'message': 'PDF Bộ Y tế võng mạc'})
        task = response.get_json()['task']
        assert task['outcome'] == 'ANSWERED'
        hit = task['evidence'][0]
        assert hit['source_type'] == 'pdf'
        assert hit['page'] == 9
        assert hit['source_url'].startswith('https://kcb.vn/')


def test_catalog_preserves_web_sources_and_counts_distinct_pdfs():
    catalog = json.loads((ROOT / 'knowledge/sources/catalog.json').read_text(encoding='utf-8'))
    sources = catalog['sources']
    split = Counter((source['source_group'], source['source_type']) for source in sources)
    assert split == {('vietnam', 'web'): 199, ('international', 'web'): 200,
                     ('vietnam', 'pdf'): 100, ('international', 'pdf'): 100}
    assert len({source['source_url'] for source in sources}) == 599
    pdf = [source['documents'][0] for source in sources if source['source_type'] == 'pdf']
    assert len({item['source_sha256'] for item in pdf}) == 200
    for evidence in pdf:
        assert evidence['local_path'].endswith('.pdf')
        assert 1 <= evidence['page'] <= evidence.get('page_count', evidence['page'])
        assert evidence['support_quotes']


@pytest.mark.skipif(os.getenv('TEST_DIABETES_NEO4J') != '1',
                    reason='Requires an imported Neo4j test instance')
def test_all_neo4j_documents_resolve_to_reviewed_evidence(web_app):
    web_app.config['DIABETES_KB_BACKEND'] = 'neo4j'
    with web_app.app_context():
        model = get_agents_model()
        health = model.health()['knowledge_backend']
        assert (health['vietnam'], health['international']) == (299, 300)
        assert (health['pdf'], health['web']) == (200, 399)
        assert health['documents'] == len(model.documents)
        for start in range(0, len(model.documents), 25):
            expected = model.documents[start:start + 25]
            hits = model.neo4j.retrieve([dict(doc_id=d['doc_id'], score=1.0) for d in expected], '')
            assert len(hits) == len(expected)
            for hit, doc in zip(hits, expected):
                assert hit['source_url'] == doc['source_url']
                assert hit['content'] == doc['summary_vi']
