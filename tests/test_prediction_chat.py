"""Conversational model routing, data collection and genuine MLP inference."""
import json

import pytest

from test_agents_project import web_app, browser, chat_request, ROOT
from mvc.controllers.agents_controller import get_agents_model

INTENT='Tôi muốn đánh giá nguy cơ tiểu đường bằng các chỉ số sức khỏe'
PROFILE=('Tôi là nữ, 47 tuổi; số lần mang thai=10; Glucose=68 mg/dL đo sau 2 giờ OGTT; '
    'huyết áp tâm trương=106 mmHg; nếp gấp da=23 mm; insulin huyết thanh sau 2 giờ=49 µU/mL; '
    'BMI=35,5; DPF=0,285')
PASTED_PROFILE='''Giới tính: Nữ
Tuổi: 53
Số lần mang thai: 6
Glucose sau 2 giờ OGTT: 215 mg/dL
Huyết áp tâm trương: 92 mmHg
Độ dày nếp gấp da: 40 mm
Insulin huyết thanh sau 2 giờ: 225 uU/mL
BMI: 37.4 kg/m2
Chỉ số phả hệ tiểu đường (DPF): 1.080'''


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


@pytest.mark.parametrize('profile,label,group',[
    (PASTED_PROFILE,1,'có tiểu đường'),(PROFILE,0,'không tiểu đường'),
])
def test_prediction_leads_with_plain_classification_and_appropriate_limits(browser,profile,label,group):
    task=chat_request(browser,INTENT+'. '+profile)['task']
    assert task['prediction']['label']==label
    assert task['reply'].startswith(f'Mô hình xếp hồ sơ vào nhóm “{group}” (nhãn {label}).')
    assert 'chưa phải chẩn đoán xác nhận' in task['reply']
    assert 'Cần bổ sung' not in task['reply']
    if label==0:
        assert 'không loại trừ bệnh' in task['reply']


@pytest.mark.parametrize('question',[
    'Vậy tôi có bị tiểu đường không?', 'Vậy tôi có bị hay không?',
    'Tôi có mắc bệnh không?', 'Kết quả này là sao?', 'Nhãn 1 là gì?',
])
def test_completed_prediction_is_explained_without_restarting_or_rerunning(browser,web_app,monkeypatch,question):
    first=chat_request(browser,PASTED_PROFILE)
    web_app.extensions.pop('chapter6_agents')
    with web_app.app_context():
        model=get_agents_model()
        model.ensure_loaded()
        monkeypatch.setattr(model.predictor,'predict',lambda *_:pytest.fail('Reuse the completed result'))
        monkeypatch.setattr(model.synthesis,'compose',lambda *_:pytest.fail('Keep personal results on server'))
    for _ in range(2):
        task=chat_request(browser,question,first['conversation_id'])['task']
        assert task['outcome']=='ANSWERED' and task['status']=='COMPLETED'
        assert task['plan']['route']=='prediction_result' and task['plan']['uses_context']
        assert task['prediction_reference']==first['task']['task_id']
        assert task['tool_calls']==0
        assert 'nhóm “có tiểu đường” (nhãn 1)' in task['reply']
        assert 'không cần nhập lại' in task['reply'] and 'Cần bổ sung' not in task['reply']
        assert any(e['action']=='EXPLAIN_PREDICTION_RESULT' for e in task['trace'])
        assert_no_model(task)


def test_demo_result_followup_never_becomes_a_personal_diagnosis(browser):
    first=chat_request(browser,'Chạy thử dự đoán bằng dữ liệu mẫu')
    task=chat_request(browser,'Vậy tôi có bị không?',first['conversation_id'])['task']
    assert task['outcome']=='ANSWERED' and task['plan']['route']=='prediction_result'
    assert 'không phải kết quả của bạn' in task['reply']
    assert_no_model(task)


def test_result_explanation_preserves_safety_and_conversation_boundaries(browser):
    first=chat_request(browser,PASTED_PROFILE)
    task=chat_request(browser,'Kết quả này là sao? Hãy kê đơn insulin',first['conversation_id'])['task']
    assert task['outcome']=='ESCALATE' and not task.get('reply')
    assert not task.get('prediction_reference')
    assert_no_model(task)
    fresh=chat_request(browser,'Vậy tôi có bị tiểu đường không?')['task']
    assert fresh['plan']['route']!='prediction_result' and not fresh.get('prediction_reference')


@pytest.mark.parametrize('question',[
    'Tiểu đường ăn chuối được không?', 'Kết quả xét nghiệm HbA1c là gì?',
    'Tiểu đường tuýp 2 là gì?', 'Tôi có mắc ung thư không?',
])
def test_other_questions_after_prediction_keep_their_own_route(browser,question):
    first=chat_request(browser,PASTED_PROFILE)
    task=chat_request(browser,question,first['conversation_id'])['task']
    assert task['plan']['route']=='knowledge' and not task.get('prediction_reference')
    assert_no_model(task)


def test_new_prediction_request_does_not_reuse_an_old_result(browser):
    first=chat_request(browser,PASTED_PROFILE)
    new=chat_request(browser,INTENT,first['conversation_id'])['task']
    assert new['outcome']=='REQUEST_INFO'
    task=chat_request(browser,'Vậy tôi có bị không?',first['conversation_id'])['task']
    assert task['plan']['route']!='prediction_result' and not task.get('prediction_reference')


@pytest.mark.parametrize('label',[
    'Chỉ số phả hệ tiểu đường (DPF): 1.080',
    'DPF (Chỉ số phả hệ tiểu đường): 1,080',
    'Chỉ số phả hệ tiểu đường [DPF] = 1.080',
    '**Chỉ số phả hệ tiểu đường (DPF)**: 1.080',
])
def test_pasted_label_and_abbreviation_are_read_as_one_field(browser,web_app,label):
    message=PASTED_PROFILE.replace('Chỉ số phả hệ tiểu đường (DPF): 1.080',label)
    first=chat_request(browser,INTENT)
    task=chat_request(browser,message,first['conversation_id'])['task']
    assert task['outcome']=='ANSWERED' and task['prediction']
    assert task['inputs']['profile']['DiabetesPedigreeFunction']==pytest.approx(1.08)
    assert 'Đã nhận đủ 8 chỉ số' in task['reply']
    with web_app.app_context():
        expected=get_agents_model().predictor.predict(task['inputs']['profile'])
    assert task['prediction']['score']==pytest.approx(expected['score'],abs=1e-7)


@pytest.mark.parametrize('after_demo',[False,True])
def test_pasted_complete_profile_activates_prediction_without_reusing_demo(browser,after_demo):
    conversation=None
    if after_demo:
        conversation=chat_request(browser,'Chạy thử dự đoán bằng dữ liệu mẫu')['conversation_id']
    task=chat_request(browser,PASTED_PROFILE,conversation)['task']
    assert task['outcome']=='ANSWERED' and task['plan']['route']=='prediction'
    assert task['inputs']['profile']==dict(Pregnancies=6,Glucose=215,BloodPressure=92,
        SkinThickness=40,Insulin=225,BMI=37.4,DiabetesPedigreeFunction=1.08,Age=53)
    assert 'dữ liệu mẫu nghiên cứu' not in task['reply']


def test_followup_only_asks_for_the_missing_value_and_accepts_annotated_dpf(browser):
    first=chat_request(browser,INTENT)
    incomplete=PASTED_PROFILE.rsplit('\n',1)[0]
    waiting=chat_request(browser,incomplete,first['conversation_id'])['task']
    assert waiting['outcome']=='REQUEST_INFO' and 'Đã nhận 7/8 chỉ số' in waiting['reply']
    assert 'Tôi có thể chạy mô hình phân loại' not in waiting['reply']
    assert 'Glucose sau 2 giờ OGTT=215' not in waiting['reply']
    result=chat_request(browser,'Chỉ số phả hệ tiểu đường (DPF): 1.080',first['conversation_id'])['task']
    assert result['outcome']=='ANSWERED' and result['prediction']


def test_conflicting_repeated_dpf_values_are_not_silently_overwritten(browser):
    first=chat_request(browser,INTENT)
    task=chat_request(browser,PASTED_PROFILE+'\nDPF=0.2',first['conversation_id'])['task']
    assert task['outcome']=='REQUEST_INFO'
    assert 'hai giá trị khác nhau' in task['reply']
    assert_no_model(task)


def test_question_with_measurements_stays_a_knowledge_question(browser):
    question='Tôi có Age=53, Glucose=215 mg/dL, BMI=37.4; tiểu đường ăn mật ong được không?'
    task=chat_request(browser,question)['task']
    assert task['plan']['route']=='knowledge'
    assert_no_model(task)
