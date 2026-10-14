# -*- coding: utf-8 -*-
"""
rag_controller.py
Tầng Controller (C) trong kiến trúc MVC cho Hệ thống Đồ thị Tri thức (Knowledge Graph)
và Kỹ thuật Tạo sinh Tăng cường Truy xuất (RAG) theo Chương 5.
"""

from flask import Blueprint, render_template, request, jsonify
from mvc.models.rag_model import RAGModel

rag_bp = Blueprint('rag', __name__, template_folder='../views')
rag_model = RAGModel()

@rag_bp.route('/rag')
def index():
    """Giao diện Dashboard Đồ thị Tri thức và GraphRAG tương tác"""
    sample_queries = [
        {
            "domain": "medical",
            "title": "Chống chỉ định Metformin ở Bệnh nhân Suy thận",
            "query": "Bệnh nhân tiểu đường có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?"
        },
        {
            "domain": "medical",
            "title": "Mục tiêu Đường huyết & Chỉ định Insulin Khẩn cấp",
            "query": "Mục tiêu HbA1c là bao nhiêu và khi nào cần khởi trị ngay bằng Insulin tiêm?"
        },
        {
            "domain": "financial",
            "title": "Động lực AWS & Rủi ro Chuỗi cung ứng AI của Amazon",
            "query": "Động lực tăng trưởng chính của Amazon hiện nay là gì và doanh nghiệp đối mặt với rủi ro chuỗi cung ứng phần cứng nào?"
        }
    ]
    
    # Kết quả khởi tạo mặc định (Medical case)
    initial_res = rag_model.query_medical(
        query=sample_queries[0]["query"],
        patient_id="B23DCCN060",
        top_k=3
    )

    return render_template(
        'rag.html',
        sample_queries=sample_queries,
        initial=initial_res,
        active_tab="rag"
    )

@rag_bp.route('/api/rag/query', methods=['POST'])
def api_rag_query():
    """Endpoint RESTful API tiếp nhận truy vấn GraphRAG đa miền (Y tế & Tài chính)"""
    data = request.get_json(force=True) or {}
    domain = data.get("domain", "medical").lower()
    query = data.get("query", "").strip()
    top_k = int(data.get("top_k", 3))

    if not query:
        return jsonify({"success": False, "error": "Truy vấn (query) không được để trống."}), 400

    if domain == "financial":
        ticker = data.get("ticker", "AMZN")
        res = rag_model.query_financial(query=query, ticker=ticker, top_k=top_k)
    else:
        patient_id = data.get("patient_id", "B23DCCN060")
        res = rag_model.query_medical(query=query, patient_id=patient_id, top_k=top_k)

    return jsonify(res)

@rag_bp.route('/api/rag/graph_elements', methods=['GET'])
def api_graph_elements():
    """Cung cấp dữ liệu đỉnh và cạnh cho thư viện Cytoscape.js"""
    domain = request.args.get("domain", "all")
    elements = rag_model.get_cytoscape_elements(domain=domain)
    return jsonify({"success": True, "elements": elements})
