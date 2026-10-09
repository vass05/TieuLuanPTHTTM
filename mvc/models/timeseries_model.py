# -*- coding: utf-8 -*-
"""
timeseries_model.py
Tầng Model (M) trong kiến trúc MVC cho bài toán Dự báo Chuỗi thời gian.
Quản lý việc nạp mô hình Keras LSTM tối ưu, bộ chuẩn hóa Scaler,
đọc dữ liệu lịch sử AMZN.csv/AEP_hourly.csv và thuật toán dự báo đa bước (Multi-step autoregressive rolling forecast).
"""

import os
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta

# TensorFlow / Keras
import tensorflow as tf

class TimeSeriesModel:
    def __init__(self, workspace_dir=None):
        if workspace_dir is None:
            workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.workspace_dir = workspace_dir
        self.model_dir = os.path.join(workspace_dir, "model")
        self.data_dir = os.path.join(workspace_dir, "DATA")
        
        self.lstm_model = None
        self.scaler = None
        self._load_artifacts()
        
    def _load_artifacts(self):
        """Nạp mô hình Keras LSTM và Scaler từ thư mục model/"""
        lstm_path = os.path.join(self.model_dir, "amzn_lstm_model.keras")
        scaler_path = os.path.join(self.model_dir, "time_series_scaler.pkl")
        
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(f"[Model Layer] Đã nạp Scaler từ: {scaler_path}")
        else:
            print(f"[Model Layer] CẢNH BÁO: Không tìm thấy Scaler tại {scaler_path}")
            
        if os.path.exists(lstm_path):
            self.lstm_model = tf.keras.models.load_model(lstm_path)
            print(f"[Model Layer] Đã nạp Keras LSTM từ: {lstm_path}")
        else:
            print(f"[Model Layer] CẢNH BÁO: Không tìm thấy mô hình LSTM tại {lstm_path}")

    def get_historical_data(self, symbol="AMZN", limit=60):
        """
        Đọc chuỗi giá lịch sử thực tế từ tập dữ liệu CSV.
        Mặc định lấy 60 phiên giao dịch gần nhất để trực quan hóa đồ thị.
        """
        if symbol.upper() == "AEP":
            csv_path = os.path.join(self.data_dir, "AEP_hourly.csv")
            if not os.path.exists(csv_path):
                return self._generate_fallback_data(symbol, limit)
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Datetime'])
            df = df.sort_values('Date').reset_index(drop=True)
            df_recent = df.tail(limit).copy()
            dates = [d.strftime("%Y-%m-%d %H:00") for d in df_recent['Date']]
            prices = [round(float(v), 2) for v in df_recent['AEP_MW']]
            unit = "MW"
            company_name = "AEP - American Electric Power (Phụ tải điện)"
        else:
            csv_path = os.path.join(self.data_dir, "AMZN.csv")
            if not os.path.exists(csv_path):
                return self._generate_fallback_data(symbol, limit)
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            df_recent = df.tail(limit).copy()
            dates = [d.strftime("%Y-%m-%d") for d in df_recent['Date']]
            prices = [round(float(v), 2) for v in df_recent['Close']]
            unit = "USD"
            company_name = "AMZN - Amazon.com Inc. (Mỹ)"

        return {
            "dates": dates,
            "prices": prices,
            "unit": unit,
            "symbol": symbol.upper(),
            "company_name": company_name,
            "last_date": dates[-1],
            "last_price": prices[-1]
        }

    def predict_future(self, history_prices, steps=7, last_date_str="2026-10-07"):
        """
        Dự báo tương lai đa bước (Multi-step autoregressive forecast)
        với cửa sổ trượt 30 phiên.
        """
        if len(history_prices) < 30:
            raise ValueError("Cần tối thiểu 30 giá trị lịch sử gần nhất để khởi tạo cửa sổ trượt.")
        
        # Lấy chính xác 30 giá trị cuối cùng
        recent_30 = np.array(history_prices[-30:], dtype=np.float32).reshape(-1, 1)
        
        if self.scaler is not None:
            scaled_window = self.scaler.transform(recent_30)
        else:
            scaled_window = recent_30.copy()
            
        current_window = scaled_window.flatten().tolist()
        predicted_scaled = []
        
        # Vòng lặp dự báo cuốn chiếu đa bước
        for _ in range(steps):
            inp = np.array(current_window[-30:], dtype=np.float32).reshape(1, 30, 1)
            if self.lstm_model is not None:
                next_val = float(self.lstm_model.predict(inp, verbose=0)[0, 0])
            else:
                # Fallback baseline nếu mô hình chưa sẵn sàng
                next_val = current_window[-1] * (1.0 + np.random.normal(0.001, 0.005))
                
            predicted_scaled.append(next_val)
            current_window.append(next_val)
            
        # Nghịch đảo chuẩn hóa về đơn vị tiền tệ thực tế
        if self.scaler is not None:
            pred_arr = np.array(predicted_scaled, dtype=np.float32).reshape(-1, 1)
            pred_real = self.scaler.inverse_transform(pred_arr).flatten().tolist()
        else:
            pred_real = predicted_scaled
            
        pred_real = [round(float(p), 2) for p in pred_real]
        
        # Sinh chuỗi ngày tương lai (bỏ qua cuối tuần)
        future_dates = self._generate_future_dates(last_date_str, steps)
        
        # Tính toán các chỉ số thống kê & biến động KPI
        last_price = float(history_prices[-1])
        t1_price = float(pred_real[0])
        final_price = float(pred_real[-1])
        
        diff_total = final_price - last_price
        pct_total = (diff_total / last_price) * 100 if last_price != 0 else 0
        trend_total = "Tăng" if diff_total >= 0 else "Giảm"
        
        diff_t1 = t1_price - last_price
        pct_t1 = (diff_t1 / last_price) * 100 if last_price != 0 else 0
        trend_t1 = "Tăng" if diff_t1 >= 0 else "Giảm"
        
        return {
            "forecast_dates": future_dates,
            "forecast_prices": pred_real,
            "last_price": last_price,
            "final_price": final_price,
            "diff_total": round(diff_total, 2),
            "pct_total": round(pct_total, 2),
            "trend_total": trend_total,
            "t1_price": t1_price,
            "diff_t1": round(diff_t1, 2),
            "pct_t1": round(pct_t1, 2),
            "trend_t1": trend_t1,
            "steps": steps
        }

    def _generate_future_dates(self, last_date_str, steps):
        """Tạo danh sách các ngày làm việc tiếp theo"""
        try:
            curr = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
        except Exception:
            curr = datetime.now()
            
        future_dates = []
        while len(future_dates) < steps:
            curr += timedelta(days=1)
            if curr.weekday() < 5:  # Thứ 2 đến Thứ 6
                future_dates.append(curr.strftime("%Y-%m-%d"))
        return future_dates

    def _generate_fallback_data(self, symbol, limit):
        """Sinh chuỗi dữ liệu dự phòng chuẩn mực"""
        now = datetime.now()
        dates = [(now - timedelta(days=limit - i)).strftime("%Y-%m-%d") for i in range(limit)]
        base = 180.0 if symbol == "AMZN" else 330.0
        prices = [round(base + np.sin(i * 0.2) * 10 + i * 0.3, 2) for i in range(limit)]
        return {
            "dates": dates, "prices": prices, "unit": "USD",
            "symbol": symbol.upper(), "company_name": f"{symbol} Stock",
            "last_date": dates[-1], "last_price": prices[-1]
        }
