"""Exercise the saved LSTM, preprocessing and Flask routes without TensorFlow."""
import io
import shutil
import zipfile
from pathlib import Path

import h5py
import numpy as np
import pytest

from mvc.models.model_errors import ModelUnavailableError
from mvc.models.timeseries_model import TimeSeriesModel

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def model():
    from mvc.controllers.timeseries_controller import ts_model
    assert ts_model.lstm_model is not None
    return ts_model


def reference_prediction(window):
    """Evaluate archived weights independently of Keras/backend loading."""
    with zipfile.ZipFile(ROOT/'model/amzn_lstm_model.keras') as archive:
        with h5py.File(io.BytesIO(archive.read('model.weights.h5')),'r') as weights:
            sequence=np.asarray(window,dtype=np.float64).reshape(30,1)
            for name in ('lstm','lstm_1'):
                kernel,recurrent,bias=[weights[f'layers/{name}/cell/vars/{i}'][()] for i in range(3)]
                hidden=np.zeros(64);cell=np.zeros(64);outputs=[]
                for value in sequence:
                    i,f,c,o=np.split(value@kernel+hidden@recurrent+bias,4)
                    sigmoid=lambda x:1/(1+np.exp(-x))
                    cell=sigmoid(f)*cell+sigmoid(i)*np.tanh(c)
                    hidden=sigmoid(o)*np.tanh(cell)
                    outputs.append(hidden)
                sequence=np.array(outputs)
            value=sequence[-1]
            for name in ('dense','dense_1'):
                value=value@weights[f'layers/{name}/vars/0'][()]+weights[f'layers/{name}/vars/1'][()]
                if name=='dense':value=np.maximum(value,0)
            return float(value[0])


def test_forecast_matches_original_weights_and_rolling_preprocessing(model):
    hist=model.get_historical_data()
    window=model.scaler.transform(np.array(hist['prices'][-30:],dtype=np.float32).reshape(-1,1)).flatten().tolist()
    expected=[]
    for _ in range(7):
        value=reference_prediction(window[-30:])
        expected.append(value);window.append(value)
    expected=model.scaler.inverse_transform(np.array(expected,dtype=np.float32).reshape(-1,1)).flatten()
    actual=model.predict_future(hist['prices'],steps=7,last_date_str=hist['last_date'])
    np.testing.assert_allclose(actual['forecast_prices'],expected,atol=.011,rtol=0)
    assert len(set(actual['forecast_prices']))>1
    assert len(actual['forecast_dates'])==7
    assert all(np.isfinite(actual['forecast_prices']))
    assert actual['forecast_dates'][3]=='2023-12-11'  # Skip the weekend in this dataset.


def test_lstm_runs_after_explicit_torch_backend_selection(monkeypatch):
    monkeypatch.setenv('KERAS_BACKEND','torch')
    actual=TimeSeriesModel(ROOT)
    assert actual.inference_backend=='torch'
    assert actual.lstm_model.input_shape==(None,30,1)
    result=actual.predict_future([100.0]*30,steps=1)
    scaled=actual.scaler.transform(np.full((30,1),100,dtype=np.float32))
    expected=actual.scaler.inverse_transform([[reference_prediction(scaled)]])[0,0]
    assert result['final_price']==pytest.approx(expected,abs=.011)


@pytest.fixture
def client(monkeypatch,model):
    from app import app
    monkeypatch.setitem(app.config,'TESTING',True)
    return app.test_client()


def test_timeseries_page_renders_the_forecast_instead_of_503(client):
    response=client.get('/timeseries')
    assert response.status_code==200
    assert b'id="stockChart"' in response.data
    assert b'const initialForecastPrices =' in response.data
    assert b'134.53' in response.data  # Actual next-step result from the saved model.


@pytest.mark.parametrize('steps',[1,7,14,30])
def test_forecast_api_returns_real_multistep_predictions(client,model,steps):
    response=client.post('/api/timeseries/forecast',json={'symbol':'AMZN','steps':steps})
    assert response.status_code==200
    data=response.get_json()
    assert data['success']
    assert len(data['forecast']['forecast_prices'])==steps
    assert data['forecast']['forecast_prices'][0]==pytest.approx(134.53,abs=.01)
    assert len(data['forecast']['forecast_dates'])==steps


def test_custom_and_legacy_routes_use_the_same_saved_model(client,model):
    prices=model.get_historical_data()['prices'][-30:]
    custom=client.post('/api/timeseries/custom_predict',json={'window_values':prices,'steps':3})
    assert custom.status_code==200
    assert len(custom.get_json()['forecast']['forecast_prices'])==3
    legacy=client.post('/api/predict_next',json={'window_values':prices})
    assert legacy.status_code==200
    assert legacy.get_json()['predicted_next_price']==custom.get_json()['forecast']['forecast_prices'][0]


@pytest.mark.parametrize('fault',['missing_model','missing_scaler','corrupt_model'])
def test_incomplete_or_corrupt_artifacts_stay_unavailable_without_fabricating_results(tmp_path,fault):
    target=tmp_path/'model';target.mkdir()
    if fault!='missing_scaler':
        shutil.copyfile(ROOT/'model/time_series_scaler.pkl',target/'time_series_scaler.pkl')
    if fault!='missing_model':
        (target/'amzn_lstm_model.keras').write_bytes(b'not a keras archive')
    actual=TimeSeriesModel(tmp_path)
    assert actual.lstm_model is None and actual.scaler is None
    with pytest.raises(ModelUnavailableError):
        actual.predict_future([100.0]*30)
