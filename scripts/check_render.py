"""Exercise every website feature offline before Render marks a build successful."""
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.environ.setdefault('MODEL_RUNTIME', 'torch_weights')
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    os.environ.setdefault('MKL_NUM_THREADS', '1')
    os.environ.setdefault('FLASK_SECRET_KEY', 'offline-build-check-only')
    # This check must never call Gemini, read market feeds or change chat history.
    os.environ['ASSISTANT_EXTERNAL_ENABLED'] = 'false'
    from app import app
    from mvc.controllers.timeseries_controller import ts_model
    from mvc.controllers.vision_controller import vision_model

    assert ts_model.lstm_model is not None, 'LSTM failed to load'
    assert vision_model.model is not None, 'Fashion SE-CNN failed to load'
    instance = ROOT / 'instance'
    instance.mkdir(exist_ok=True)
    folder = instance / ('render-check-' + uuid.uuid4().hex)
    folder.mkdir()
    try:
        app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False,
                          AGENTS_DATABASE=str(Path(folder) / 'tasks.sqlite3'))
        client = app.test_client()
        for path in ('/healthz', '/agents', '/housing', '/vision', '/rag', '/timeseries?source=amzn_csv'):
            assert client.get(path).status_code == 200, 'Page failed: ' + path
        health = client.get('/api/v1/health')
        assert health.status_code == 200 and health.json['knowledge'], 'Local KB failed'
        config = client.get('/api/v1/agents/session').json
        headers = {'X-CSRF-Token': config['csrf_token']}
        chat = client.post('/api/v1/assistant/chat', json={'message': 'Tieu duong tuyp 2 la gi?'}, headers=headers)
        assert chat.status_code == 200 and chat.json['task']['outcome'] == 'ANSWERED', 'Chat failed'
        assert chat.json['task']['evidence'][0]['doc_id'] == 'K01', 'Unexpected KB evidence'
        example = config['config']['examples'][0]
        prediction = client.post('/api/v1/predict', json={'profile': example['profile']}, headers=headers)
        assert prediction.status_code == 200 and prediction.json['prediction'] is not None, 'Pima MLP failed'
        housing = client.post('/api/housing/predict', json={'area': 75, 'bedroom': 2, 'toilet': 2, 'floors': 1})
        assert housing.status_code == 200 and housing.json['success'], 'Housing prediction failed'
        for task in ('fashion', 'digits'):
            with (ROOT / 'tests/fixtures/digits/2.png').open('rb') as handle:
                image = client.post('/api/vision/predict', data={'task': task, 'image_file': (handle, '2.png')})
            assert image.status_code == 200 and image.json['success'], 'Vision failed: ' + task
        assert 'keras' not in sys.modules, 'Compact deployment unexpectedly loaded Keras'
        print('Render check passed: all five pages, local KB/chat, Pima MLP, housing, LSTM, fashion and MNIST.')
    finally:
        # Only remove the isolated SQLite files created by this check.
        for name in ('tasks.sqlite3', 'tasks.sqlite3-journal', 'tasks.sqlite3-wal', 'tasks.sqlite3-shm'):
            (folder / name).unlink(missing_ok=True)
        folder.rmdir()


if __name__ == '__main__':
    main()
