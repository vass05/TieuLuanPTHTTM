# -*- coding: utf-8 -*-
"""
vision_controller.py
Tầng Controller (C) trong kiến trúc MVC cho bài toán Thị giác máy tính (Fashion-MNIST).
Xử lý tải lên hình ảnh, tiếp nhận nét vẽ từ Canvas HTML5 và gọi VisionModel để nhận diện.
"""

from flask import Blueprint, render_template, request, jsonify
from mvc.models.vision_model import VisionModel

vision_bp = Blueprint('vision', __name__, template_folder='../views')
vision_model = VisionModel()

@vision_bp.route('/vision')
def index():
    """Giao diện nhận diện sản phẩm thời trang bằng SE-Block CNN"""
    return render_template(
        'vision.html',
        classes=VisionModel.CLASSES,
        active_tab="vision"
    )

@vision_bp.route('/api/vision/predict', methods=['POST'])
def api_predict():
    """Endpoint API nhận diện ảnh từ file tải lên hoặc nét vẽ Canvas"""
    # 1. Kiểm tra nếu gửi tệp qua multipart/form-data
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename != '':
            img_bytes = file.read()
            res = vision_model.predict_image(img_bytes)
            return jsonify({"success": True, "result": res})
            
    # 2. Kiểm tra nếu gửi chuỗi Base64 qua JSON
    data = request.get_json(silent=True) or {}
    img_b64 = data.get('image_base64', '')
    if img_b64:
        res = vision_model.predict_image(img_b64)
        return jsonify({"success": True, "result": res})
        
    return jsonify({"success": False, "error": "Không tìm thấy dữ liệu hình ảnh hợp lệ."}), 400
