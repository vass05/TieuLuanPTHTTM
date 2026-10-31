# -*- coding: utf-8 -*-
"""
timeseries_controller.py
Tầng Controller (C) trong kiến trúc MVC cho bài toán Dự báo Chuỗi thời gian.
Xử lý các HTTP Request, kết nối với TimeSeriesModel và trả về dữ liệu/view tương ứng.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from mvc.models.timeseries_model import TimeSeriesModel
from mvc.models.market_data import MarketData, MarketDataUnavailable
from werkzeug.exceptions import BadRequest

timeseries_bp = Blueprint('timeseries', __name__, template_folder='../views')
ts_model = TimeSeriesModel()
market_data = MarketData(ts_model.workspace_dir)


@timeseries_bp.errorhandler(BadRequest)
def bad_request(error):
    if request.path.startswith('/api/'):
        return jsonify(success=False,error=error.description),400
    return error.get_response()


def forecast_options(values):
    symbol=values.get('symbol','AMZN')
    source=values.get('source','live')
    if source=='dataset':source='live'  # Old clients called this option "real time".
    try:
        steps=int(values.get('steps',7))
    except (ValueError,TypeError):
        raise BadRequest('Số bước dự báo phải là số nguyên từ 1 đến 30.')
    raw_steps=values.get('steps',7)
    if isinstance(raw_steps,bool) or (isinstance(raw_steps,float) and raw_steps!=steps):
        raise BadRequest('Số bước dự báo phải là số nguyên từ 1 đến 30.')
    if not isinstance(symbol,str) or symbol.upper() not in ('AMZN','AEP'):
        raise BadRequest('Mã dữ liệu không hợp lệ.')
    symbol=symbol.upper()
    if source not in ('live','amzn_csv','aep_csv') or not 1<=steps<=30:
        raise BadRequest('Nguồn dữ liệu hoặc số bước dự báo không hợp lệ.')
    if (source in ('live','amzn_csv') and symbol!='AMZN') or (source=='aep_csv' and symbol!='AEP'):
        raise BadRequest('Nguồn trực tuyến và AMZN.csv dùng AMZN; AEP_hourly.csv dùng mã AEP.')
    return symbol,steps,source


def history_for_source(symbol,source):
    if source=='live':
        return market_data.history(symbol=symbol,limit=60)
    hist=ts_model.get_historical_data(symbol=symbol,limit=60)
    hist.update(source=source,is_live=False,source_label=('Tệp AMZN.csv · Dữ liệu lịch sử' if source=='amzn_csv'
        else 'Tệp AEP_hourly.csv · Phụ tải điện lịch sử'),source_url=None,fetched_at=None)
    return hist

@timeseries_bp.route('/timeseries')
def index():
    """Trang chủ hiển thị Bảng điều khiển dự báo giá cổ phiếu (Giao diện chuẩn tham khảo)"""
    symbol,steps,source = forecast_options(request.args)
    
    # Lấy dữ liệu lịch sử và thực hiện dự báo ban đầu
    try:
        hist_data = history_for_source(symbol,source)
    except MarketDataUnavailable as error:
        return render_template('timeseries_unavailable.html',message=str(error),active_tab='market'),503
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
    if not isinstance(data,dict):raise BadRequest('Dữ liệu yêu cầu phải là một đối tượng JSON.')
    symbol,steps,source = forecast_options(data)
    
    hist_data = history_for_source(symbol,source)
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
