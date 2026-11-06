#!/usr/bin/env bash
set -euo pipefail

python -m pip install --no-cache-dir -r requirements-render.txt
python scripts/check_render.py
