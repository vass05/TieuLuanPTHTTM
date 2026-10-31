# -*- coding: utf-8 -*-
"""
vision_controller.py
Tầng Controller (C) trong kiến trúc MVC cho bài toán Thị giác máy tính (Fashion-MNIST).
Xử lý tải lên hình ảnh, tiếp nhận nét vẽ từ Canvas HTML5 và gọi VisionModel để nhận diện.
"""

from flask import Blueprint, render_template, request, jsonify
from mvc.models.vision_model import VisionModel
from mvc.models.digit_model import DigitModel

vision_bp = Blueprint('vision', __name__, template_folder='../views')
vision_model = VisionModel()
digit_model = DigitModel()


@vision_bp.errorhandler(ValueError)
def invalid_image(error):
    return jsonify(success=False,error=str(error)),400

@vision_bp.route('/vision')
def index():
    """Giao diện nhận diện sản phẩm thời trang bằng SE-Block CNN"""
    return render_template(
        'vision.html',
        classes=VisionModel.CLASSES,
        digit_accuracy=digit_model.metadata().get('test_accuracy'),
        active_tab="vision"
    )

@vision_bp.route('/api/vision/predict', methods=['POST'])
def api_predict():
    """Endpoint API nhận diện ảnh từ file tải lên hoặc nét vẽ Canvas"""
    if 'image_file' in request.files:
        file = request.files['image_file']
        image=file.read() if file and file.filename else None
        task=request.form.get('task','fashion')
    else:
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):
            return jsonify(success=False,error='Nội dung yêu cầu phải là một đối tượng JSON.'),400
        image=data.get('image_base64')
        task=data.get('task','fashion')
    if task not in ('fashion','digits'):
        return jsonify(success=False,error='Chọn nhận diện thời trang hoặc chữ số 0–9.'),400
    if not image:
        return jsonify(success=False,error='Không tìm thấy dữ liệu hình ảnh hợp lệ.'),400
    classifier=digit_model if task=='digits' else vision_model
    return jsonify(success=True,result=classifier.predict_image(image),task=task)
