# -*- coding: utf-8 -*-
"""
timeseries_controller.py
Tầng Controller (C) trong kiến trúc MVC cho bài toán Dự báo Chuỗi thời gian.
Xử lý các HTTP Request, kết nối với TimeSeriesModel và trả về dữ liệu/view tương ứng.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from mvc.models.timeseries_model import TimeSeriesModel

timeseries_bp = Blueprint('timeseries', __name__, template_folder='../views')
ts_model = TimeSeriesModel()

@timeseries_bp.route('/')
@timeseries_bp.route('/timeseries')
def index():
    """Trang chủ hiển thị Bảng điều khiển dự báo giá cổ phiếu (Giao diện chuẩn tham khảo)"""
    symbol = request.args.get('symbol', 'AMZN')
    steps = int(request.args.get('steps', 7))
    source = request.args.get('source', 'dataset')
    
    # Lấy dữ liệu lịch sử và thực hiện dự báo ban đầu
    hist_data = ts_model.get_historical_data(symbol=symbol, limit=60)
    forecast_data = ts_model.predict_future(
        history_prices=hist_data['prices'],
        steps=steps,
        last_date_str=hist_data['last_date']
    )
    
    return render_template(
        'timeseries.html',
        symbol=symbol,
        steps=steps,
        source=source,
        hist=hist_data,
        forecast=forecast_data,
        active_tab="market"
    )

@timeseries_bp.route('/custom')
def custom_view():
    """Đã loại bỏ trang tùy biến theo yêu cầu, chuyển hướng về trang dự báo chính"""
    return redirect(url_for('timeseries.index'))

@timeseries_bp.route('/api/timeseries/forecast', methods=['POST'])
def api_forecast():
    """Endpoint API AJAX cho giao diện cập nhật biểu đồ không cần load lại trang"""
    data = request.get_json(force=True) or {}
    symbol = data.get('symbol', 'AMZN')
    steps = int(data.get('steps', 7))
    source = data.get('source', 'dataset')
    
    hist_data = ts_model.get_historical_data(symbol=symbol, limit=60)
    forecast_data = ts_model.predict_future(
        history_prices=hist_data['prices'],
        steps=steps,
        last_date_str=hist_data['last_date']
    )
    
    return jsonify({
        "success": True,
        "hist": hist_data,
        "forecast": forecast_data,
        "meta": {
            "symbol": symbol,
            "steps": steps,
            "source": source
        }
    })

@timeseries_bp.route('/api/timeseries/custom_predict', methods=['POST'])
def api_custom_predict():
    """Endpoint API dự báo từ chuỗi 30 giá trị tùy biến người dùng nhập vào"""
    data = request.get_json(force=True) or {}
    raw_vals = data.get('window_values', [])
    steps = int(data.get('steps', 7))
    
    if len(raw_vals) < 30:
        return jsonify({"success": False, "error": f"Cần tối thiểu 30 giá trị (hiện có: {len(raw_vals)})."}), 400
        
    prices = [float(x) for x in raw_vals[-30:]]
    forecast_data = ts_model.predict_future(history_prices=prices, steps=steps)
    
    return jsonify({
        "success": True,
        "forecast": forecast_data,
        "input_prices": prices
    })
