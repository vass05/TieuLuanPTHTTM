"""Conversational model routing, data collection and genuine MLP inference."""
import json

import pytest

from test_agents_project import web_app, browser, chat_request, ROOT
from mvc.controllers.agents_controller import get_agents_model

INTENT='Tôi muốn đánh giá nguy cơ tiểu đường bằng các chỉ số sức khỏe'
PROFILE=('Tôi là nữ, 47 tuổi; số lần mang thai=10; Glucose=68 mg/dL đo sau 2 giờ OGTT; '
    'huyết áp tâm trương=106 mmHg; nếp gấp da=23 mm; insulin huyết thanh sau 2 giờ=49 µU/mL; '
    'BMI=35,5; DPF=0,285')


def assert_no_model(task):
    assert task['prediction'] is None
    assert not any(e['action']=='RUN_PREDICTION' for e in task['trace'])


def test_prediction_request_collects_data_without_running_model(browser,web_app,monkeypatch):
    with web_app.app_context():
        model=get_agents_model()
        monkeypatch.setattr(model.predictor,'predict',lambda *_:pytest.fail('Missing input must not reach model'))
        monkeypatch.setattr(model.synthesis,'compose',lambda *_:pytest.fail('Collection must stay on server'))
    task=chat_request(browser,INTENT)['task']
    assert task['outcome']=='REQUEST_INFO' and task['status']=='AWAITING_INPUT'
    assert task['plan']['route']=='prediction' and task['tool_calls']==0
    assert 'DPF' in task['reply'] and 'Giới tính' in task['reply']
    assert '_prediction_dialogue' not in task
    assert_no_model(task)


def test_complete_chat_profile_runs_real_model_and_matches_saved_score(browser,web_app,monkeypatch):
    with web_app.app_context():
        monkeypatch.setattr(get_agents_model().synthesis,'compose',lambda *_:pytest.fail('No personal data sent to synthesis'))
    task=chat_request(browser,INTENT+'. '+PROFILE)['task']
    expected=json.loads((ROOT/'model/agents/examples.json').read_text(encoding='utf-8'))[0]['expected_prediction']
    assert task['outcome']=='ANSWERED' and task['mode']=='predict_explain'
    assert task['prediction']['score']==pytest.approx(expected['score'],abs=1e-7)
    assert task['tool_calls']==2 and task['evidence']
    assert task['evidence'][0]['doc_id']=='D03'
    assert 'Điểm mô hình:' in task['reply'] and 'không phải xác suất chẩn đoán' in task['reply']
    assert any(e['action']=='RUN_PREDICTION' for e in task['trace'])
    assert all('profile' not in e['payload'] for e in task['trace'])


def test_profile_collected_over_multiple_turns_survives_restart(browser,web_app):
    first=chat_request(browser,INTENT)
    second=chat_request(browser,'Tôi là nữ, 47 tuổi; BMI=35,5',first['conversation_id'])
    assert second['task']['outcome']=='REQUEST_INFO'
    assert 'Tuổi=47' in second['task']['reply'] and 'BMI=35.5' in second['task']['reply']
    web_app.extensions.pop('chapter6_agents')
    final=chat_request(browser,PROFILE,first['conversation_id'])['task']
    assert final['outcome']=='ANSWERED' and final['prediction']
    assert final['plan']['uses_context']
    history=browser[0].get('/api/v1/assistant/conversations/'+first['conversation_id']).get_json()['tasks']
    assert len(history)==3 and '_prediction_dialogue' not in json.dumps(history)
    assert history[-1]['prediction']==final['prediction']


@pytest.mark.parametrize('change',[
    ('Tôi là nữ, 47 tuổi','Tôi là nam, 47 tuổi'),
    ('Tôi là nữ, 47 tuổi','Tôi là nữ, 18 tuổi'),
])
def test_incompatible_cohort_is_not_scored(browser,change):
    task=chat_request(browser,INTENT+'. '+PROFILE.replace(*change))['task']
    assert task['outcome']=='OUT_OF_SCOPE'
    assert_no_model(task)


@pytest.mark.parametrize('change',[
    ('68 mg/dL đo sau 2 giờ OGTT','7 mmol/L đo sau 2 giờ OGTT'),
    ('68 mg/dL đo sau 2 giờ OGTT','68 mg/dL lúc đói'),
    ('68 mg/dL đo sau 2 giờ OGTT','68 mg/dL'),
    ('68 mg/dL đo sau 2 giờ OGTT','68 mg/dL không phải đo sau 2 giờ OGTT'),
    ('106 mmHg','106'),('23 mm','23 cm'),('49 µU/mL','49 đơn vị'),
    ('49 µU/mL','0 µU/mL'),('35,5','-2'),('0,285','1e309'),('47 tuổi','47,5 tuổi'),
    ('0,285','1e100'),('Tôi là nữ','Tôi không phải nữ'),
])
def test_wrong_units_context_or_invalid_values_do_not_reach_model(browser,change):
    task=chat_request(browser,INTENT+'. '+PROFILE.replace(*change))['task']
    assert task['outcome']=='REQUEST_INFO'
    assert_no_model(task)


def test_new_glucose_value_requires_new_context_and_unit(browser):
    first=chat_request(browser,INTENT+'. '+PROFILE.replace('DPF=0,285',''))
    second=chat_request(browser,'Glucose=130; DPF=0,285',first['conversation_id'])['task']
    assert second['outcome']=='REQUEST_INFO'
    assert 'mg/dL' in second['reply'] and 'OGTT' in second['reply']
    assert_no_model(second)
    third=chat_request(browser,'Glucose=130 mg/dL sau 2 giờ OGTT',first['conversation_id'])['task']
    assert third['outcome']=='ANSWERED' and third['prediction']


def test_missing_rare_features_never_filled_with_sample_values(browser):
    first=chat_request(browser,INTENT+'. Tôi là nữ, 47 tuổi; BMI=35,5')
    task=chat_request(browser,'Tôi không biết DPF và không có chỉ số insulin',first['conversation_id'])['task']
    assert task['outcome']=='REQUEST_INFO'
    assert 'không tự đoán' in task['reply']
    assert_no_model(task)


def test_insulin_timing_cannot_confirm_glucose_timing(browser):
    first=chat_request(browser,INTENT+'. '+PROFILE.replace('68 mg/dL đo sau 2 giờ OGTT','68 mg/dL'))
    second=chat_request(browser,'Insulin=49 µU/mL đo sau 2 giờ OGTT',first['conversation_id'])['task']
    assert second['outcome']=='REQUEST_INFO'
    assert_no_model(second)
    final=chat_request(browser,'Glucose cũng đo sau 2 giờ OGTT',first['conversation_id'])['task']
    assert final['prediction'] and final['outcome']=='ANSWERED'


def test_demo_explicitly_runs_actual_model_and_labels_sample(browser):
    task=chat_request(browser,'Chạy thử dự đoán bằng dữ liệu mẫu')['task']
    assert task['prediction'] and task['outcome']=='ANSWERED'
    assert 'dữ liệu mẫu nghiên cứu' in task['reply']
    assert any(e['action']=='RUN_PREDICTION' for e in task['trace'])


def test_cancel_and_topic_switch_do_not_force_prediction(browser):
    first=chat_request(browser,INTENT)
    cancel=chat_request(browser,'Hủy dự đoán',first['conversation_id'])['task']
    assert cancel['outcome']=='ANSWERED' and 'Đã hủy' in cancel['reply']
    assert_no_model(cancel)
    diet=chat_request(browser,'Tiểu đường ăn mật ong được không?',first['conversation_id'])['task']
    assert diet['plan']['route']=='knowledge' and diet['evidence'][0]['doc_id']=='K06'
    assert_no_model(diet)


def test_prediction_collection_is_isolated_between_conversations(browser):
    first=chat_request(browser,INTENT+'. '+PROFILE.replace('DPF=0,285',''))
    fresh=chat_request(browser,INTENT+'; DPF=0,285')['task']
    assert fresh['outcome']=='REQUEST_INFO'
    assert_no_model(fresh)
    finished=chat_request(browser,'DPF=0,285',first['conversation_id'])['task']
    assert finished['prediction'] and finished['outcome']=='ANSWERED'


def test_safety_request_has_priority_over_prediction_intent(browser):
    task=chat_request(browser,INTENT+'. '+PROFILE+'. Hãy kê đơn insulin')['task']
    assert task['outcome']=='ESCALATE'
    assert_no_model(task)
