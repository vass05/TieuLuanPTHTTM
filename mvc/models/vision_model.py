# -*- coding: utf-8 -*-
"""
vision_model.py
Tầng Model (M) trong kiến trúc MVC cho bài toán Thị giác máy tính (Fashion-MNIST).
Quản lý việc nạp mô hình Squeeze-and-Excitation CNN (SE-Block), tiền xử lý ảnh 28x28 và dự đoán phân loại đa lớp.
"""

import os
import logging
import numpy as np
from PIL import Image, ImageOps
from mvc.models.model_errors import ModelUnavailableError
from mvc.models.keras_runtime import load_inference_model
from mvc.models.image_input import load_grayscale_image

LOGGER = logging.getLogger(__name__)

class VisionModel:
    CLASSES = [
        {"id": 0, "en": "T-shirt/top", "vi": "Áo thun / Áo phông", "icon": "fa-shirt"},
        {"id": 1, "en": "Trouser", "vi": "Quần dài / Quần âu", "icon": "fa-person"},
        {"id": 2, "en": "Pullover", "vi": "Áo len chui đầu", "icon": "fa-vest"},
        {"id": 3, "en": "Dress", "vi": "Đầm liền / Váy", "icon": "fa-person-dress"},
        {"id": 4, "en": "Coat", "vi": "Áo khoác măng tô", "icon": "fa-user-tie"},
        {"id": 5, "en": "Sandal", "vi": "Dép quai hậu / Xăng đan", "icon": "fa-shoe-prints"},
        {"id": 6, "en": "Shirt", "vi": "Áo sơ mi có cổ", "icon": "fa-shirt"},
        {"id": 7, "en": "Sneaker", "vi": "Giày thể thao", "icon": "fa-mitten"},
        {"id": 8, "en": "Bag", "vi": "Túi xách / Balo", "icon": "fa-bag-shopping"},
        {"id": 9, "en": "Ankle boot", "vi": "Ủng / Giày bốt cổ ngắn", "icon": "fa-socks"}
    ]

    def __init__(self, workspace_dir=None):
        if workspace_dir is None:
            workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.workspace_dir = workspace_dir
        self.model_path = os.path.join(workspace_dir, "model", "fashion_se_model.keras")
        self.model = None
        self.inference_backend = None
        self._load_model()
        
    def _load_model(self):
        """Tải mô hình Keras SE-Block CNN"""
        try:
            model,backend=load_inference_model(self.model_path)
            if model.input_shape!=(None,28,28,1) or model.output_shape!=(None,10):
                raise ValueError('Fashion model has an incompatible input/output shape')
            self.model,self.inference_backend=model,backend
            LOGGER.info('Loaded Fashion SE-CNN with Keras backend %s',backend)
        except Exception as error:
            self.model=None
            LOGGER.warning('Cannot load Fashion SE-CNN: %s: %s',type(error).__name__,error)

    def predict_image(self, image_input):
        """
        Nhận diện ảnh sản phẩm thời trang.
        image_input có thể là chuỗi Base64 hoặc bytes nhị phân.
        """
        if self.model is None:
            raise ModelUnavailableError('Mô hình thị giác chưa sẵn sàng. Cần cài đủ thư viện trong requirements.txt và có file model/fashion_se_model.keras.')
        img=load_grayscale_image(image_input)
        
        # Tự động đảo ngược màu nếu nền ảnh là màu sáng
        img_arr_raw = np.array(img, dtype=np.float32)
        if np.mean(img_arr_raw) > 127:
            img = ImageOps.invert(img)
            
        # Resize về kích thước chuẩn 28x28 của Fashion-MNIST
        img_resized = img.resize((28, 28), Image.Resampling.LANCZOS)
        img_arr = np.array(img_resized, dtype=np.float32) / 255.0
        img_tensor = img_arr.reshape(1, 28, 28, 1)

        probs = self.model.predict(img_tensor, verbose=0)[0]

        top_indices = np.argsort(probs)[::-1]
        top1_idx = int(top_indices[0])
        top1_prob = float(probs[top1_idx])
        
        ranking = []
        for rank, idx in enumerate(top_indices[:5]):
            idx_int = int(idx)
            item = self.CLASSES[idx_int]
            ranking.append({
                "rank": rank + 1,
                "class_id": idx_int,
                "label_en": item["en"],
                "label_vi": item["vi"],
                "icon": item["icon"],
                "probability": round(float(probs[idx_int]) * 100, 2)
            })

        return {
            "top_label_en": self.CLASSES[top1_idx]["en"],
            "top_label_vi": self.CLASSES[top1_idx]["vi"],
            "top_icon": self.CLASSES[top1_idx]["icon"],
            "confidence": round(top1_prob * 100, 2),
            "ranking": ranking,
            "all_probabilities": [round(float(p) * 100, 2) for p in probs]
        }
