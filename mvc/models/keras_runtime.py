"""Chọn backend suy luận cho các mô hình đã lưu ở định dạng Keras."""
import importlib.util
import os
from pathlib import Path


def load_inference_model(path):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    runtime = os.environ.get('MODEL_RUNTIME', 'keras')
    # Render đọc trực tiếp trọng số từ tệp Keras qua bộ suy luận PyTorch.
    if runtime == 'torch_weights':
        from mvc.models.torch_keras_runtime import load_saved_model
        return load_saved_model(path), 'torch'
    if runtime != 'keras':
        raise ValueError('MODEL_RUNTIME must be keras or torch_weights')
    # Keras đọc backend lúc import lần đầu. setdefault giữ cấu hình người dùng đã đặt.
    os.environ.setdefault('KERAS_BACKEND',
        'tensorflow' if importlib.util.find_spec('tensorflow') is not None else 'torch')
    import keras
    # Chỉ nạp để suy luận nên bỏ qua bước biên dịch cho huấn luyện.
    return keras.models.load_model(path,compile=False),keras.backend.backend()
