#!/usr/bin/env bash
set -euo pipefail

# Cài bộ phụ thuộc CPU dùng trên Render rồi chạy thử các chức năng bằng mô hình đã lưu.
python -m pip install --no-cache-dir -r requirements-render.txt
python scripts/check_render.py
