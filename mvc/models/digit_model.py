"""MNIST-only digit classifier; never reuse fashion weights for digit labels."""
import hashlib
import json
import threading
from pathlib import Path

import numpy as np
import torch
from PIL import Image,ImageOps
from torch import nn

from mvc.models.image_input import load_grayscale_image
from mvc.models.model_errors import ModelUnavailableError


class DigitCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.Sequential(
            nn.Conv2d(1,32,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(32,64,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Flatten(),
            nn.Linear(64*7*7,128),nn.ReLU(),nn.Dropout(.3),nn.Linear(128,10))

    def forward(self,x):
        return self.layers(x)


def normalize_digit(image):
    """Crop ink, preserve its aspect ratio in 20x20 and center it on 28x28."""
    image=image.convert('L')
    values=np.asarray(image)
    border=np.concatenate((values[0],values[-1],values[:,0],values[:,-1]))
    if np.median(border)>127:
        image=ImageOps.invert(image);values=np.asarray(image)
    ink=np.argwhere(values>25)
    if not len(ink):
        raise ValueError('Chưa thấy nét chữ. Hãy viết một chữ số từ 0 đến 9 rồi bấm nhận diện.')
    top,left=ink.min(axis=0);bottom,right=ink.max(axis=0)+1
    crop=image.crop((int(left),int(top),int(right),int(bottom)))
    scale=20/max(crop.size)
    crop=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('L',(28,28),0)
    canvas.paste(crop,((28-crop.width)//2,(28-crop.height)//2))
    values=np.asarray(canvas,dtype=np.float32)/255
    yy,xx=np.indices(values.shape)
    total=values.sum()
    dx=round(13.5-float((values*xx).sum()/total));dy=round(13.5-float((values*yy).sum()/total))
    canvas=canvas.transform((28,28),Image.Transform.AFFINE,(1,0,-dx,0,1,-dy),fillcolor=0)
    return np.array(canvas,dtype=np.float32)/255


class DigitModel:
    def __init__(self,workspace_dir=None):
        self.root=Path(workspace_dir) if workspace_dir else Path(__file__).resolve().parents[2]
        self.model_path=self.root/'model/vision/mnist_cnn_state.pt'
        self.manifest_path=self.root/'model/vision/mnist_cnn_manifest.json'
        self.model=None
        self._lock=threading.RLock()

    def metadata(self):
        if not self.manifest_path.is_file():return {}
        return json.loads(self.manifest_path.read_text(encoding='utf-8'))

    def ensure_loaded(self):
        with self._lock:
            if self.model is not None:return
            try:
                metadata=self.metadata()
                if metadata.get('architecture')!='digit_cnn_v1' or metadata.get('preprocessing')!='crop20_com_v1':
                    raise ValueError('Incompatible digit model metadata')
                if hashlib.sha256(self.model_path.read_bytes()).hexdigest()!=metadata['weights_sha256']:
                    raise ValueError('Digit model checksum mismatch')
                model=DigitCNN()
                model.load_state_dict(torch.load(self.model_path,map_location='cpu',weights_only=True))
                self.model=model.eval()
            except Exception as error:
                raise ModelUnavailableError('Chưa nạp được mô hình chữ số MNIST. Hãy kiểm tra bộ trọng số chữ số của project.') from error

    def predict_image(self,image_input):
        self.ensure_loaded()
        values=normalize_digit(load_grayscale_image(image_input))
        with torch.inference_mode():
            probabilities=torch.softmax(self.model(torch.from_numpy(values).reshape(1,1,28,28)),dim=1)[0].numpy()
        order=np.argsort(probabilities)[::-1]
        digit=int(order[0])
        return dict(task='digits',digit=digit,top_label_vi=f'Số {digit}',top_label_en=f'Digit {digit}',
            top_icon='fa-hashtag',confidence=round(float(probabilities[digit])*100,2),
            all_probabilities=[round(float(p)*100,2) for p in probabilities],
            ranking=[dict(rank=rank+1,class_id=int(index),label_vi=f'Số {index}',label_en=f'Digit {index}',
                icon='fa-hashtag',probability=round(float(probabilities[index])*100,2)) for rank,index in enumerate(order[:5])])
