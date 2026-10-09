# -*- coding: utf-8 -*-
"""
housing_controller.py
Tầng Controller (C) trong kiến trúc MVC cho bài toán Định giá Bất động sản (Vietnam Housing).
Xử lý tương tác người dùng, gọi HousingModel và hiển thị giao diện định giá BĐS thông minh.
"""

from flask import Blueprint, render_template, request, jsonify
from mvc.models.housing_model import HousingModel

housing_bp = Blueprint('housing', __name__, template_folder='../views')
house_model = HousingModel()

@housing_bp.route('/housing')
def index():
    """Giao diện định giá bất động sản thông minh bằng XGBoost"""
    sample_presets = [
        {"name": "Căn hộ Studio / 1PN", "area": 35.0, "bedroom": 1, "toilet": 1, "floors": 1},
        {"name": "Chung cư Gia đình 2PN", "area": 68.0, "bedroom": 2, "toilet": 2, "floors": 1},
        {"name": "Nhà phố Đô thị 3 tầng", "area": 85.0, "bedroom": 3, "toilet": 3, "floors": 3},
        {"name": "Biệt thự Liền kề 4 tầng", "area": 160.0, "bedroom": 5, "toilet": 4, "floors": 4}
    ]
    initial_res = house_model.predict_price(area=75.0, bedroom=3, toilet=2, floors=2)
    return render_template(
        'housing.html',
        presets=sample_presets,
        initial=initial_res,
        active_tab="housing"
    )

@housing_bp.route('/api/housing/predict', methods=['POST'])
def api_predict():
    """Endpoint API định giá bất động sản thời gian thực"""
    data = request.get_json(force=True) or {}
    area = float(data.get('area', 75.0))
    bedroom = float(data.get('bedroom', 3.0))
    toilet = float(data.get('toilet', 2.0))
    floors = float(data.get('floors', 2.0))
    
    res = house_model.predict_price(area, bedroom, toilet, floors)
    return jsonify({"success": True, "result": res})
