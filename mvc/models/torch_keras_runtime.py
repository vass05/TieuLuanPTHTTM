"""CPU inference for the two shipped Keras archives, without importing Keras.

The config fingerprints restrict this adapter to the exact supported architectures.
Weights are read directly from the original archives; no training or conversion
of repository artifacts takes place. Dropout is inactive during inference.
"""
import hashlib
import io
import zipfile

import h5py
import numpy as np
import torch
from torch.nn import functional as F


CONFIGS = {
    '3ef47b9b08e2f700b5656d9b11a98ab521daec6991c40071a50525c2cb38c0c2': 'lstm',
    'e2d2257b7ea08ae80f3df7852308fc77954cf947c96929d62f873c3629824704': 'fashion',
}


class SavedModel:
    def __init__(self, architecture, weights):
        self.architecture = architecture
        self.weights = weights
        self.input_shape = (None, 30, 1) if architecture == 'lstm' else (None, 28, 28, 1)
        self.output_shape = (None, 1) if architecture == 'lstm' else (None, 10)

    def dense(self, values, name):
        return values @ self.weights[name + '/0'] + self.weights[name + '/1']

    def predict(self, values, verbose=0):
        values = np.asarray(values, dtype=np.float32)
        if values.ndim != len(self.input_shape) or tuple(values.shape[1:]) != self.input_shape[1:]:
            raise ValueError('Input shape does not match the saved model')
        if not np.isfinite(values).all():
            raise ValueError('Model input must contain finite values')
        with torch.inference_mode():
            inputs = torch.from_numpy(values)
            outputs = self._lstm(inputs) if self.architecture == 'lstm' else self._fashion(inputs)
            return outputs.numpy()

    def _lstm(self, sequence):
        for name in ('lstm/cell', 'lstm_1/cell'):
            kernel, recurrent, bias = (self.weights[name + '/' + str(i)] for i in range(3))
            hidden = torch.zeros((sequence.shape[0], 64))
            cell = torch.zeros_like(hidden)
            outputs = []
            # Keras gate ordering is input, forget, candidate, output.
            for value in sequence.unbind(dim=1):
                i, f, candidate, o = (value @ kernel + hidden @ recurrent + bias).chunk(4, dim=1)
                cell = torch.sigmoid(f) * cell + torch.sigmoid(i) * torch.tanh(candidate)
                hidden = torch.sigmoid(o) * torch.tanh(cell)
                outputs.append(hidden)
            sequence = torch.stack(outputs, dim=1)
        return self.dense(F.relu(self.dense(sequence[:, -1], 'dense')), 'dense_1')

    def _fashion(self, inputs):
        kernel = self.weights['conv2d/0'].permute(3, 2, 0, 1).contiguous()
        features = F.max_pool2d(F.relu(F.conv2d(
            inputs.permute(0, 3, 1, 2), kernel, self.weights['conv2d/1'], padding=1)), 2)
        attention = torch.sigmoid(self.dense(F.relu(self.dense(features.mean(dim=(2, 3)), 'dense')), 'dense_1'))
        # Preserve Keras channels-last flattening before the dense layers.
        features = (features * attention[:, :, None, None]).permute(0, 2, 3, 1).reshape(inputs.shape[0], -1)
        return torch.softmax(self.dense(F.relu(self.dense(features, 'dense_2')), 'dense_3'), dim=1)


def load_saved_model(path):
    with zipfile.ZipFile(path) as archive:
        fingerprint = hashlib.sha256(archive.read('config.json')).hexdigest()
        architecture = CONFIGS.get(fingerprint)
        if architecture is None:
            raise ValueError('Unsupported model config for the compact runtime; use MODEL_RUNTIME=keras')
        shapes = ({
            'lstm/cell': [(1, 256), (64, 256), (256,)],
            'lstm_1/cell': [(64, 256), (64, 256), (256,)],
            'dense': [(64, 32), (32,)], 'dense_1': [(32, 1), (1,)],
        } if architecture == 'lstm' else {
            'conv2d': [(3, 3, 1, 32), (32,)],
            'dense': [(32, 2), (2,)], 'dense_1': [(2, 32), (32,)],
            'dense_2': [(6272, 64), (64,)], 'dense_3': [(64, 10), (10,)],
        })
        tensors = {}
        with h5py.File(io.BytesIO(archive.read('model.weights.h5')), 'r') as weights:
            for name, expected in shapes.items():
                for index, shape in enumerate(expected):
                    # The HDF5 variable group belongs to the LSTM cell itself.
                    values = weights[f'layers/{name}/vars/{index}'][()]
                    if values.shape != shape or values.dtype != np.float32 or not np.isfinite(values).all():
                        raise ValueError('Invalid saved weights for the compact runtime')
                    tensors[f'{name}/{index}'] = torch.from_numpy(values)
    return SavedModel(architecture, tensors)
