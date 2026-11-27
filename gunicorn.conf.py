"""Dùng một worker để giới hạn số bản sao mô hình trong bộ nhớ trên Render."""
import os

bind = '0.0.0.0:' + os.environ.get('PORT', '10000')
workers = 1
worker_class = 'gthread'
threads = 2
timeout = 120
graceful_timeout = 30
accesslog = '-'
errorlog = '-'
# Cho worker nạp ứng dụng và mô hình. Tiến trình chính chỉ quản lý worker.
preload_app = False
