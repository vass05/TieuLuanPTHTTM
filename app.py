# -*- coding: utf-8 -*-
"""
app.py - Main Entrypoint cho Hệ thống Ứng dụng Thông minh theo Kiến trúc MVC
Tích hợp các mô hình học máy và trợ lý tiểu đường:
1. Model Dự Báo Chuỗi Thời Gian (Keras LSTM - AMZN.csv / AEP_hourly.csv)
2. Model Định Giá Bất Động Sản (XGBoost Regressor - Vietnam Housing)
3. Model Thị Giác Máy Tính (SE-Block CNN - Fashion-MNIST)
4. Trợ lý tiểu đường (MLP, tri thức có nguồn, Rule-Based/Q-learning)
"""

import os
import sys
import socket
import secrets
from pathlib import Path
from flask import Flask, jsonify, request, redirect, url_for

try:
    if hasattr(sys.stdout, 'reconfigure'):
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
except Exception:
    pass

# Import các tầng Controller (C)
from mvc.controllers.timeseries_controller import timeseries_bp, ts_model
from mvc.controllers.housing_controller import housing_bp, house_model
from mvc.controllers.vision_controller import vision_bp, vision_model
from mvc.controllers.rag_controller import rag_bp
from mvc.controllers.agents_controller import agents_bp
from mvc.models.model_errors import ModelUnavailableError

# Khởi tạo ứng dụng Flask với đường dẫn MVC views và static
app = Flask(
    __name__,
    template_folder="mvc/views",
    static_folder="mvc/static"
)
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.json.ensure_ascii = False
# A local persistent signing key keeps task ownership valid across restarts.
# The instance directory is excluded from version control.
instance_dir = Path(app.instance_path)
instance_dir.mkdir(parents=True, exist_ok=True)
secret_file = instance_dir / 'session_secret.key'
if os.environ.get('FLASK_SECRET_KEY'):
    app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
else:
    try:
        with secret_file.open('x', encoding='ascii') as secret_handle:
            secret_handle.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    app.config['SECRET_KEY'] = secret_file.read_text(encoding='ascii').strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  AGENTS_DATABASE=str(instance_dir / 'agents.sqlite3'))

# Đăng ký các Blueprints
app.register_blueprint(timeseries_bp)
app.register_blueprint(housing_bp)
app.register_blueprint(vision_bp)
app.register_blueprint(rag_bp)
app.register_blueprint(agents_bp)


@app.route('/')
def index():
    return redirect(url_for('agents.index'))

# Đồng bộ tương thích ngược với các endpoint cũ của 3 API đơn lẻ + RAG
legacy_housing_model = house_model
legacy_vision_model = vision_model
legacy_ts_model = ts_model


@app.errorhandler(ModelUnavailableError)
def model_unavailable(error):
    if request.path.startswith('/api/'):
        return jsonify(success=False,error=str(error)),503
    from flask import render_template
    return render_template('model_unavailable.html',message=str(error)),503

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
