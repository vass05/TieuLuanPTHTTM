"""Compact deployment must preserve inference from the archived models."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

from mvc.models.keras_runtime import load_inference_model
from mvc.models.torch_keras_runtime import load_saved_model
from test_timeseries_runtime import reference_prediction
from test_vision_runtime import pixels, reference_probabilities

ROOT = Path(__file__).resolve().parents[1]


def test_compact_lstm_matches_archived_gates_for_varied_windows():
    model = load_saved_model(ROOT / 'model/amzn_lstm_model.keras')
    windows = np.stack([np.zeros((30, 1)), np.ones((30, 1)),
                        np.linspace(-1, 2, 30).reshape(30, 1),
                        np.random.default_rng(42).normal(size=(30, 1))]).astype(np.float32)
    expected = [reference_prediction(window) for window in windows]
    np.testing.assert_allclose(model.predict(windows)[:, 0], expected, atol=2e-6, rtol=1e-5)


def test_compact_fashion_matches_archived_attention_and_channels_last_flattening():
    model = load_saved_model(ROOT / 'model/fashion_se_model.keras')
    image = (pixels().astype(np.float32) / 255).reshape(1, 28, 28, 1)
    np.testing.assert_allclose(model.predict(image)[0], reference_probabilities(), atol=1e-6, rtol=1e-5)
    batch = model.predict(np.concatenate([image, 1 - image]))
    assert batch.shape == (2, 10)
    np.testing.assert_allclose(batch.sum(axis=1), 1, atol=1e-6)


def test_compact_loader_rejects_changed_architecture(tmp_path):
    source = ROOT / 'model/amzn_lstm_model.keras'
    with zipfile.ZipFile(source) as archive:
        config = json.loads(archive.read('config.json'))
    config['config']['layers'][1]['config']['activation'] = 'relu'
    target = tmp_path / 'changed.keras'
    with zipfile.ZipFile(target, 'w') as archive:
        archive.writestr('config.json', json.dumps(config))
    with pytest.raises(ValueError, match='Unsupported model config'):
        load_saved_model(target)


def test_runtime_selection_and_invalid_input(monkeypatch):
    monkeypatch.setenv('MODEL_RUNTIME', 'torch_weights')
    model, backend = load_inference_model(ROOT / 'model/amzn_lstm_model.keras')
    assert backend == 'torch'
    with pytest.raises(ValueError, match='shape'):
        model.predict(np.zeros((1, 29, 1)))
    with pytest.raises(ValueError, match='finite'):
        model.predict(np.full((1, 30, 1), np.nan))


def test_all_website_features_in_a_fresh_compact_process():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_render.py')],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Render check passed' in result.stdout
