"""Load saved Keras weights for inference using an available backend."""
import importlib.util
import os
from pathlib import Path


def load_inference_model(path):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    # Backend selection must precede the first Keras import. Keep user settings.
    os.environ.setdefault('KERAS_BACKEND',
        'tensorflow' if importlib.util.find_spec('tensorflow') is not None else 'torch')
    import keras
    return keras.models.load_model(path,compile=False),keras.backend.backend()
