"""Load saved Keras weights for inference using an available backend."""
import importlib.util
import os
from pathlib import Path


def load_inference_model(path):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    runtime = os.environ.get('MODEL_RUNTIME', 'keras')
    if runtime == 'torch_weights':
        from mvc.models.torch_keras_runtime import load_saved_model
        return load_saved_model(path), 'torch'
    if runtime != 'keras':
        raise ValueError('MODEL_RUNTIME must be keras or torch_weights')
    # Backend selection must precede the first Keras import. Keep user settings.
    os.environ.setdefault('KERAS_BACKEND',
        'tensorflow' if importlib.util.find_spec('tensorflow') is not None else 'torch')
    import keras
    return keras.models.load_model(path,compile=False),keras.backend.backend()
