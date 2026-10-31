"""Real SE-CNN inference, image input variants and HTTP error behavior."""
import base64
import io
import zipfile
from pathlib import Path

import h5py
import numpy as np
import pytest
import torch
from PIL import Image
from torch.nn import functional as F

from mvc.models.model_errors import ModelUnavailableError
from mvc.models.vision_model import VisionModel

ROOT=Path(__file__).resolve().parents[1]


def pixels():
    image=np.zeros((28,28),dtype=np.uint8)
    image[10:24,6:23]=200
    image[4:11,10:19]=220
    image[6:10,12:17]=0
    return image


def png(image=None):
    buffer=io.BytesIO()
    Image.fromarray(pixels() if image is None else image).save(buffer,format='PNG')
    return buffer.getvalue()


@pytest.fixture(scope='module')
def model():
    from mvc.controllers.vision_controller import vision_model
    assert vision_model.model is not None
    return vision_model


def reference_probabilities():
    """Evaluate the archived SE weights independently of Keras deserialization."""
    with zipfile.ZipFile(ROOT/'model/fashion_se_model.keras') as archive:
        with h5py.File(io.BytesIO(archive.read('model.weights.h5')),'r') as weights:
            def w(layer,index):return torch.from_numpy(weights[f'layers/{layer}/vars/{index}'][()])
            def dense(x,layer):return x@w(layer,0)+w(layer,1)
            with torch.inference_mode():
                image=torch.from_numpy(pixels().astype(np.float32)/255).reshape(1,1,28,28)
                features=F.max_pool2d(F.relu(F.conv2d(image,w('conv2d',0).permute(3,2,0,1),w('conv2d',1),padding=1)),2)
                attention=torch.sigmoid(dense(F.relu(dense(features.mean(dim=(2,3)),'dense')),'dense_1'))
                features=(features*attention[:,:,None,None]).permute(0,2,3,1).reshape(1,-1)
                logits=dense(F.relu(dense(features,'dense_2')),'dense_3')
                return torch.softmax(logits,dim=1).numpy()[0]


def test_se_model_matches_original_weights(model):
    result=model.predict_image(png())
    expected=reference_probabilities()
    np.testing.assert_allclose(result['all_probabilities'],expected*100,atol=.011,rtol=0)
    assert result['top_label_en']==VisionModel.CLASSES[int(expected.argmax())]['en']
    assert len(result['ranking'])==5
    assert sum(result['all_probabilities'])==pytest.approx(100,abs=.06)
    assert [r['probability'] for r in result['ranking']]==sorted([r['probability'] for r in result['ranking']],reverse=True)


@pytest.mark.parametrize('as_data_url',[False,True])
def test_canvas_base64_matches_binary_input(model,as_data_url):
    image=png();encoded=base64.b64encode(image).decode('ascii')
    if as_data_url:encoded='data:image/png;base64,'+encoded
    assert model.predict_image(encoded)==model.predict_image(image)


def test_white_background_and_transparent_pngs_have_consistent_preprocessing(model):
    expected=model.predict_image(png())
    assert model.predict_image(png(255-pixels()))==expected
    rgba=np.zeros((28,28,4),dtype=np.uint8)
    rgba[:,:,3]=pixels()
    assert model.predict_image(png(rgba))==expected


@pytest.fixture
def client(monkeypatch,model):
    from app import app
    monkeypatch.setitem(app.config,'TESTING',True)
    return app.test_client()


def test_draw_endpoint_returns_real_prediction(client,model):
    image='data:image/png;base64,'+base64.b64encode(png()).decode('ascii')
    response=client.post('/api/vision/predict',json={'image_base64':image})
    assert response.status_code==200
    assert response.get_json()['result']==model.predict_image(png())


def test_upload_endpoint_and_legacy_endpoint_match_canvas_result(client,model):
    expected=model.predict_image(png())
    response=client.post('/api/vision/predict',data={'image_file':(io.BytesIO(png()),'sample.png')})
    assert response.status_code==200 and response.get_json()['result']==expected
    legacy=client.post('/api/predict_image',json={'image_base64':base64.b64encode(png()).decode('ascii')})
    assert legacy.status_code==200
    assert legacy.get_json()['top_prediction']==expected['top_label_en']
    assert legacy.get_json()['confidence']==expected['confidence']


@pytest.mark.parametrize('body',[
    {},{'image_base64':'not base64!'},
    {'image_base64':base64.b64encode(b'not an image').decode('ascii')},
    {'image_base64':42},['invalid request'],
])
def test_invalid_images_return_json_400_instead_of_500(client,body):
    response=client.post('/api/vision/predict',json=body)
    assert response.status_code==400
    assert not response.get_json()['success']


def test_invalid_uploaded_image_is_reported_as_input_error(client):
    response=client.post('/api/vision/predict',data={'image_file':(io.BytesIO(b'bad image'),'sample.png')})
    assert response.status_code==400 and not response.get_json()['success']


@pytest.mark.parametrize('corrupt',[False,True])
def test_missing_or_corrupt_saved_model_does_not_fabricate_predictions(tmp_path,corrupt):
    if corrupt:
        target=tmp_path/'model';target.mkdir()
        (target/'fashion_se_model.keras').write_bytes(b'not a keras model')
    model=VisionModel(tmp_path)
    assert model.model is None
    with pytest.raises(ModelUnavailableError):model.predict_image(png())


def test_model_failure_keeps_503_and_an_explanatory_json_message(client,monkeypatch):
    import mvc.controllers.vision_controller as controller
    monkeypatch.setattr(controller.vision_model,'model',None)
    response=client.post('/api/vision/predict',json={'image_base64':base64.b64encode(png()).decode('ascii')})
    assert response.status_code==503
    assert not response.get_json()['success'] and 'error' in response.get_json()
