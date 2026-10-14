# -*- coding: utf-8 -*-
"""
app_rag_api.py
Máy chủ RESTful API Backend độc lập cho Hệ thống GraphRAG theo Mục 5.7.2.
Tiếp nhận truy vấn kiểm chứng chéo đa miền (Y tế & Tài chính), trả về JSON phản hồi chuẩn hóa.
"""

import os
import sys
import time
from flask import Flask, request, jsonify
from mvc.models.rag_model import RAGModel

try:
    if hasattr(sys.stdout, 'reconfigure'):
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
except Exception:
    pass

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Khởi tạo mô hình RAG
rag_engine = RAGModel()

@app.route('/api/rag/query', methods=['POST'])
def rag_query_endpoint():
    """
    Endpoint chuẩn hóa theo đặc tả Mục 5.7.2 của Tiểu luận
    Method: POST
    Payload:
    {
      "domain": "medical" | "financial",
      "patient_id": "B23DCCN060",  (đối với Y tế)
      "ticker": "AMZN",             (đối với Tài chính)
      "query": "...",
      "top_k": 3
    }
    """
    data = request.get_json(force=True) or {}
    domain = data.get("domain", "medical").lower()
    query = data.get("query", "").strip()
    top_k = int(data.get("top_k", 3))

    if not query:
        return jsonify({"success": False, "error": "Truy vấn (query) không được để trống."}), 400

    if domain == "financial":
        ticker = data.get("ticker", "AMZN")
        res = rag_engine.query_financial(query=query, ticker=ticker, top_k=top_k)
    else:
        patient_id = data.get("patient_id", "B23DCCN060")
        res = rag_engine.query_medical(query=query, patient_id=patient_id, top_k=top_k)

    return jsonify(res), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "GraphRAG Microservice", "version": "2.0"})

if __name__ == '__main__':
    port = int(os.environ.get('RAG_PORT', 5003))
    print("=" * 65)
    print(f"MÁY CHỦ FLASK RAG API ĐỘC LẬP ĐANG KHỞI CHẠY TRÊN CỔNG {port}")
    print(f"[-] Endpoint kiểm tra: http://127.0.0.1:{port}/api/rag/query")
    print("=" * 65)
    app.run(host='0.0.0.0', port=port, debug=False)
