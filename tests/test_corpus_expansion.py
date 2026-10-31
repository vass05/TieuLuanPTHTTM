"""Serving corpus growth, source provenance and practical question relevance."""
import json
import re

import pytest

from test_agents_project import web_app,browser,chat_request,ROOT

CASES=json.loads((ROOT/'tests/diabetes_expansion_questions.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('question,expected',CASES)
def test_new_questions_select_the_specific_source(browser,question,expected):
    task=chat_request(browser,question)['task']
    assert task['outcome']=='ANSWERED'
    assert task['evidence'][0]['doc_id']==expected
    assert task['blocks'] and all(b['evidence_ids'] for b in task['blocks'])
    assert task['prediction'] is None
    if expected=='K33':
        assert 'có thể ăn chuối' in task['blocks'][0]['text']
        assert 'K01' not in {h['doc_id'] for h in task['evidence']}


def test_new_corpus_is_126_distinct_sources_with_provenance():
    data=json.loads((ROOT/'knowledge/diabetes_expansion.json').read_text(encoding='utf-8'))
    docs=data['documents']
    assert len(docs)==126
    assert len({d['doc_id'] for d in docs})==126
    assert len({d['source_url'].rstrip('/') for d in docs})==126
    assert len({d['summary_vi'] for d in docs})==126
    assert len({d['category'] for d in docs})>=7
    for doc in docs:
        assert re.fullmatch(r'[0-9a-f]{64}',doc['source_sha256'])
        assert doc['http_status']==200
        assert doc['retrieved_on']=='2026-10-31'
        assert 35<=len(doc['summary_vi'].split())<=125
        assert 0<sum(len(q.split()) for q in doc['support_quotes'])<=16
        assert 'clinical' not in doc['review_method']
    report=json.loads((ROOT/'reports/project/corpus_source_review.json').read_text(encoding='utf-8'))
    assert {r['doc_id'] for r in report['review']}=={d['doc_id'] for d in docs}


def test_specific_topic_outranks_an_incidental_mention(browser):
    task=chat_request(browser,'Nhiễm toan ceton là gì?')['task']
    assert task['evidence'][0]['doc_id']=='K16'
    assert 'Nhiễm toan ceton là biến chứng' in task['blocks'][0]['text']
