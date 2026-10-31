"""Task separation, saved MNIST inference and handwritten-image preparation."""
import base64
import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image,ImageOps

from mvc.models.digit_model import DigitModel,normalize_digit
from mvc.models.model_errors import ModelUnavailableError

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/digits'


@pytest.fixture(scope='module')
def model():
    return DigitModel(ROOT)


def png(image):
    stream=io.BytesIO();image.save(stream,format='PNG');return stream.getvalue()


@pytest.mark.parametrize('digit',range(10))
def test_official_test_examples_are_classified_as_digits(model,digit):
    result=model.predict_image((FIXTURES/f'{digit}.png').read_bytes())
    assert result['task']=='digits' and result['digit']==digit
    assert result['top_label_vi']==f'Số {digit}'
    assert len(result['all_probabilities'])==10 and len(result['ranking'])==5
    assert sum(result['all_probabilities'])==pytest.approx(100,abs=.06)
    assert result['ranking'][0]['class_id']==digit


def test_manifest_records_independent_full_test_evaluation(model):
    metadata=model.metadata()
    assert metadata['train_samples']==54000 and metadata['validation_samples']==6000
    assert metadata['test_samples']==10000 and metadata['test_accuracy']>=.98
    assert metadata['classes']==list(range(10))
    report=json.loads((ROOT/'reports/project/mnist_training.json').read_text(encoding='utf-8'))
    confusion=np.array(report['confusion_matrix'])
    assert confusion.sum()==10000
    assert confusion.trace()/confusion.sum()==pytest.approx(metadata['test_accuracy'])


def test_data_url_white_background_and_transparency_produce_same_digit(model):
    image=Image.open(FIXTURES/'3.png').convert('L')
    expected=model.predict_image(png(image))
    encoded='data:image/png;base64,'+base64.b64encode(png(image)).decode('ascii')
    assert model.predict_image(encoded)==expected
    assert model.predict_image(png(ImageOps.invert(image)))==expected
    rgba=Image.new('RGBA',image.size,(0,0,0,0));rgba.putalpha(image)
    assert model.predict_image(png(rgba))==expected


def test_digit_is_cropped_and_centered_after_canvas_resize(model):
    image=ImageOps.invert(Image.open(FIXTURES/'3.png').convert('L')).resize((112,112))
    canvas=Image.new('L',(280,280),255);canvas.paste(image,(30,80))
    result=model.predict_image(png(canvas))
    assert result['digit']==3
    values=normalize_digit(canvas)
    yy,xx=np.indices(values.shape)
    assert abs((values*xx).sum()/values.sum()-13.5)<1
    assert abs((values*yy).sum()/values.sum()-13.5)<1


@pytest.mark.parametrize('background',[0,255])
def test_blank_canvas_does_not_invent_a_digit(model,background):
    with pytest.raises(ValueError,match='0 đến 9'):
        model.predict_image(png(Image.new('L',(280,280),background)))


def test_missing_or_tampered_weights_fail_closed(tmp_path,model):
    actual=DigitModel(tmp_path)
    with pytest.raises(ModelUnavailableError):actual.predict_image((FIXTURES/'3.png').read_bytes())
    actual.model_path.parent.mkdir(parents=True)
    actual.manifest_path.write_text(json.dumps(model.metadata()),encoding='utf-8')
    actual.model_path.write_bytes(b'corrupt weights')
    with pytest.raises(ModelUnavailableError):actual.predict_image((FIXTURES/'3.png').read_bytes())


@pytest.fixture
def client(monkeypatch):
    from app import app
    monkeypatch.setitem(app.config,'TESTING',True)
    return app.test_client()


def test_digits_canvas_and_upload_never_call_fashion_model(client,monkeypatch):
    import mvc.controllers.vision_controller as controller
    monkeypatch.setattr(controller.vision_model,'predict_image',lambda *_:pytest.fail('Digits must use their own model'))
    image=(FIXTURES/'3.png').read_bytes()
    canvas=client.post('/api/vision/predict',json={'task':'digits','image_base64':base64.b64encode(image).decode('ascii')})
    assert canvas.status_code==200 and canvas.get_json()['result']['digit']==3
    upload=client.post('/api/vision/predict',data={'task':'digits','image_file':(io.BytesIO(image),'digit.png')})
    assert upload.status_code==200 and upload.get_json()['result']==canvas.get_json()['result']


def test_default_fashion_task_never_calls_digit_model(client,monkeypatch):
    import mvc.controllers.vision_controller as controller
    monkeypatch.setattr(controller.digit_model,'predict_image',lambda *_:pytest.fail('Fashion must keep its own model'))
    image=(FIXTURES/'3.png').read_bytes()
    response=client.post('/api/vision/predict',json={'image_base64':base64.b64encode(image).decode('ascii')})
    assert response.status_code==200 and response.get_json()['task']=='fashion'
    assert 'digit' not in response.get_json()['result']


@pytest.mark.parametrize('task',['unknown',None,42,['digits']])
def test_unknown_task_is_rejected(client,task):
    response=client.post('/api/vision/predict',json={'task':task,'image_base64':'anything'})
    assert response.status_code==400 and not response.get_json()['success']


def test_digit_task_does_not_fall_back_when_its_weights_are_missing(client,monkeypatch,tmp_path):
    import mvc.controllers.vision_controller as controller
    monkeypatch.setattr(controller,'digit_model',DigitModel(tmp_path))
    image=(FIXTURES/'3.png').read_bytes()
    response=client.post('/api/vision/predict',json={'task':'digits','image_base64':base64.b64encode(image).decode('ascii')})
    assert response.status_code==503 and not response.get_json()['success']
