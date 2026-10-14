# -*- coding: utf-8 -*-
"""
app.py - Main Entrypoint cho Hệ thống Ứng dụng Thông minh theo Kiến trúc MVC
Tích hợp trọn vẹn 3 mô hình học máy tối ưu:
1. Model Dự Báo Chuỗi Thời Gian (Keras LSTM - AMZN.csv / AEP_hourly.csv)
2. Model Định Giá Bất Động Sản (XGBoost Regressor - Vietnam Housing)
3. Model Thị Giác Máy Tính (SE-Block CNN - Fashion-MNIST)
"""

import os
import sys
import socket
from flask import Flask, jsonify, request

try:
    if hasattr(sys.stdout, 'reconfigure'):
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
except Exception:
    pass

# Import các tầng Controller (C)
from mvc.controllers.timeseries_controller import timeseries_bp
from mvc.controllers.housing_controller import housing_bp
from mvc.controllers.vision_controller import vision_bp
from mvc.controllers.rag_controller import rag_bp

# Khởi tạo ứng dụng Flask với đường dẫn MVC views và static
app = Flask(
    __name__,
    template_folder="mvc/views",
    static_folder="mvc/static"
)
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Đăng ký các Blueprints
app.register_blueprint(timeseries_bp)
app.register_blueprint(housing_bp)
app.register_blueprint(vision_bp)
app.register_blueprint(rag_bp)

# Đồng bộ tương thích ngược với các endpoint cũ của 3 API đơn lẻ + RAG
from mvc.models.housing_model import HousingModel
from mvc.models.vision_model import VisionModel
from mvc.models.timeseries_model import TimeSeriesModel
from mvc.models.rag_model import RAGModel

legacy_housing_model = HousingModel()
legacy_vision_model = VisionModel()
legacy_ts_model = TimeSeriesModel()
legacy_rag_model = RAGModel()
legacy_vision_model = VisionModel()
legacy_ts_model = TimeSeriesModel()

@app.route('/api/predict', methods=['POST'])
def legacy_housing_predict():
    """Tương thích ngược app_housing_api.py"""
    data = request.get_json(force=True) or {}
    area = float(data.get('area', 50))
    bedroom = float(data.get('bedroom', 2))
    toilet = float(data.get('toilet', 1))
    floors = float(data.get('floors', 2))
    res = legacy_housing_model.predict_price(area, bedroom, toilet, floors)
    return jsonify({
        "success": True,
        "model": "XGBoost Regressor",
        "predicted_price_billion": res["predicted_price_billion"],
        "price_per_m2_million": res["price_per_m2_million"],
        "segment": res["segment"]
    })

@app.route('/api/predict_image', methods=['POST'])
def legacy_vision_predict():
    """Tương thích ngược app_vision_api.py"""
    data = request.get_json(force=True) or {}
    img_b64 = data.get('image_base64', '')
    res = legacy_vision_model.predict_image(img_b64)
    return jsonify({
        "success": True,
        "top_prediction": res["top_label_en"],
        "top_prediction_vi": res["top_label_vi"],
        "confidence": res["confidence"]
    })

@app.route('/api/predict_next', methods=['POST'])
def legacy_ts_predict():
    """Tương thích ngược app_timeseries_api.py"""
    data = request.get_json(force=True) or {}
    window_vals = data.get('window_values', [])
    if len(window_vals) < 30:
        return jsonify({"success": False, "error": "Yêu cầu tối thiểu 30 giá trị lịch sử."}), 400
    res = legacy_ts_model.predict_future(history_prices=window_vals, steps=1)
    return jsonify({
        "success": True,
        "symbol": data.get("symbol", "AMZN"),
        "predicted_next_price": res["final_price"],
        "trend": res["trend_total"]
    })

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    ip = get_local_ip()
    print("=" * 65)
    print("HỆ THỐNG WEB APP THÔNG MINH KIẾN TRÚC MVC ĐÃ KHỞI CHẠY THÀNH CÔNG!")
    print(f"[-] Địa chỉ cục bộ:  http://127.0.0.1:{port}")
    print(f"[-] Mạng nội bộ IP: http://{ip}:{port}")
    print("=" * 65)
    app.run(host='0.0.0.0', port=port, debug=False)
