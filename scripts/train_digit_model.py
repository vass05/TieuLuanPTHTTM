"""Train the separate digit CNN; no downloads or training occur in web requests."""
import argparse
import copy
import gzip
import hashlib
import json
import struct
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
import pandas as pd
import requests
import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.nn import functional as F
from torch.utils.data import DataLoader,TensorDataset

from mvc.models.digit_model import DigitCNN,normalize_digit


def official_test(cache):
    resources=[('t10k-images-idx3-ubyte.gz','9fb629c4189551a2d022fa330f9573f3'),
               ('t10k-labels-idx1-ubyte.gz','ec29112dd5afa0611ce80d1b7f02629c')]
    session=requests.Session();session.trust_env=False
    arrays=[]
    for name,digest in resources:
        path=cache/name
        if not path.exists():
            response=session.get('https://ossci-datasets.s3.amazonaws.com/mnist/'+name,timeout=30)
            response.raise_for_status();content=response.content
            if hashlib.md5(content).hexdigest()!=digest:raise ValueError('MNIST download checksum mismatch')
            path.write_bytes(content)
        if hashlib.md5(path.read_bytes()).hexdigest()!=digest:raise ValueError('MNIST cache checksum mismatch')
        raw=gzip.decompress(path.read_bytes())
        if name.startswith('t10k-images'):
            assert struct.unpack('>4I',raw[:16])==(2051,10000,28,28)
            arrays.append(np.frombuffer(raw,dtype=np.uint8,offset=16).reshape(10000,28,28))
        else:
            assert struct.unpack('>2I',raw[:8])==(2049,10000)
            arrays.append(np.frombuffer(raw,dtype=np.uint8,offset=8).astype(np.int64))
    return arrays


def prepared(images,path):
    if path.exists():return np.load(path)['images']
    values=np.stack([normalize_digit(Image.fromarray(image)) for image in images])
    np.savez_compressed(path,images=values)
    return values


def augment(batch):
    angle=(torch.rand(len(batch))*24-12)*np.pi/180
    scale=torch.rand(len(batch))*.2+.9
    matrix=torch.zeros(len(batch),2,3)
    matrix[:,0,0]=torch.cos(angle)*scale;matrix[:,0,1]=-torch.sin(angle)*scale
    matrix[:,1,0]=torch.sin(angle)*scale;matrix[:,1,1]=torch.cos(angle)*scale
    matrix[:,:,2]=(torch.rand(len(batch),2)-.5)*.2
    return F.grid_sample(batch,F.affine_grid(matrix,batch.shape,align_corners=False),align_corners=False)


def evaluate(model,loader):
    model.eval();correct=0;predictions=[]
    with torch.inference_mode():
        for inputs,labels in loader:
            pred=model(inputs).argmax(1);correct+=int((pred==labels).sum());predictions.extend(pred.tolist())
    return correct/len(loader.dataset),np.array(predictions)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--epochs',type=int,default=6)
    parser.add_argument('--batch-size',type=int,default=256);parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args()
    torch.set_num_threads(args.threads);torch.manual_seed(42);np.random.seed(42)
    cache=ROOT/'.ipynb_checkpoints'/'digit-training';cache.mkdir(parents=True,exist_ok=True)
    csv=ROOT/'DATA/mnist_train.csv';digest=hashlib.sha256(csv.read_bytes()).hexdigest()
    data=pd.read_csv(csv,dtype=np.uint8).to_numpy()
    assert data.shape==(60000,785)
    labels=data[:,0].astype(np.int64)
    print('Preparing 60,000 MNIST training images',flush=True)
    images=prepared(data[:,1:].reshape(-1,28,28),cache/('training-'+digest[:12]+'-crop20.npz'))
    test_images,test_labels=official_test(cache)
    test=prepared(test_images,cache/'official-test-crop20.npz')
    train_idx,val_idx=train_test_split(np.arange(len(labels)),test_size=.1,stratify=labels,random_state=42)
    def loader(x,y,shuffle=False):
        return DataLoader(TensorDataset(torch.from_numpy(x[:,None]),torch.from_numpy(y)),batch_size=args.batch_size,shuffle=shuffle)
    train=loader(images[train_idx],labels[train_idx],True)
    val=loader(images[val_idx],labels[val_idx]);test_loader=loader(test,test_labels)
    model=DigitCNN();optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    best_accuracy=0;best_state=None;history=[];started=time.monotonic()
    for epoch in range(args.epochs):
        model.train();total_loss=0
        for inputs,target in train:
            optimizer.zero_grad(set_to_none=True)
            loss=F.cross_entropy(model(augment(inputs)),target)
            loss.backward();optimizer.step();total_loss+=float(loss.detach())*len(target)
        accuracy,_=evaluate(model,val)
        history.append(dict(epoch=epoch+1,training_loss=total_loss/len(train.dataset),validation_accuracy=accuracy))
        print(json.dumps(history[-1]),flush=True)
        if accuracy>best_accuracy:best_accuracy=accuracy;best_state=copy.deepcopy(model.state_dict())
        if epoch==3:
            for group in optimizer.param_groups:group['lr']=.0003
    model.load_state_dict(best_state)
    test_accuracy,predictions=evaluate(model,test_loader)
    if best_accuracy<.98 or test_accuracy<.98:raise RuntimeError('Digit model did not meet the evaluation threshold')
    output=ROOT/'model/vision';output.mkdir(parents=True,exist_ok=True)
    path=output/'mnist_cnn_state.pt';torch.save(best_state,path)
    metadata=dict(architecture='digit_cnn_v1',preprocessing='crop20_com_v1',classes=list(range(10)),
        weights_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),training_csv_sha256=digest,
        train_samples=len(train_idx),validation_samples=len(val_idx),test_samples=len(test_labels),
        validation_accuracy=best_accuracy,test_accuracy=test_accuracy,seed=42,epochs=args.epochs,
        torch_version=str(torch.__version__),created_at=datetime.now(timezone.utc).isoformat(),
        test_source='https://ossci-datasets.s3.amazonaws.com/mnist/',
        test_resources=[dict(name=n,md5=d) for n,d in [('t10k-images-idx3-ubyte.gz','9fb629c4189551a2d022fa330f9573f3'),('t10k-labels-idx1-ubyte.gz','ec29112dd5afa0611ce80d1b7f02629c')]])
    (output/'mnist_cnn_manifest.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    confusion=np.zeros((10,10),dtype=int)
    for actual,predicted in zip(test_labels,predictions):confusion[actual,predicted]+=1
    report=dict(**metadata,history=history,confusion_matrix=confusion.tolist(),duration_seconds=round(time.monotonic()-started,2))
    (ROOT/'reports/project/mnist_training.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    fixtures=ROOT/'tests/fixtures/digits';fixtures.mkdir(parents=True,exist_ok=True)
    examples=[]
    for digit in range(10):
        index=int(np.flatnonzero(test_labels==digit)[0])
        Image.fromarray(test_images[index]).save(fixtures/f'{digit}.png')
        examples.append(dict(file=f'{digit}.png',official_test_index=index,label=digit))
    (fixtures/'source.json').write_text(json.dumps(dict(source=metadata['test_source'],examples=examples),indent=2),encoding='utf-8')
    print(json.dumps(dict(test_accuracy=test_accuracy,validation_accuracy=best_accuracy,weights=str(path))),flush=True)


if __name__=='__main__':main()
