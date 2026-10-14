# -*- coding: utf-8 -*-
"""
rag_controller.py
Tầng Controller (C) trong kiến trúc MVC cho Hệ thống Trợ lý Y khoa Thông minh GraphRAG Chatbot.
"""

from typing import Any, Optional
from flask import Blueprint, render_template, request, jsonify
from mvc.models.rag_model import RAGModel

rag_bp = Blueprint('rag', __name__, template_folder='../views')
rag_model = RAGModel()

@rag_bp.route('/rag')
def index():
    """Giao diện Trợ lý Y khoa Thông minh & Đồ thị Tri thức Đàm thoại"""
    session_id, session_data = rag_model.get_or_create_session()
    
    # Gợi ý tình huống lâm sàng khởi tạo
    quick_prompts = [
        {
            "icon": "fa-triangle-exclamation",
            "title": "Chống chỉ định Metformin",
            "query": "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?"
        },
        {
            "icon": "fa-syringe",
            "title": "Phác đồ chuyển sang Insulin",
            "query": "Khi eGFR dưới 30 thì chuyển sang Insulin nền liều lượng như thế nào?"
        },
        {
            "icon": "fa-heart-pulse",
            "title": "Bảo vệ Tim - Thận (SGLT-2i)",
            "query": "Bệnh nhân tiểu đường có suy tim thì dùng Dapagliflozin có lợi ích gì?"
        },
        {
            "icon": "fa-store",
            "title": "Báo giá Trajenta tại Long Châu",
            "query": "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?"
        },
        {
            "icon": "fa-prescription-bottle-medical",
            "title": "Mua Glucophage & Đơn Rx",
            "query": "Tôi ra Long Châu mua Glucophage 500mg uống được không, có cần đơn bác sĩ không?"
        },
        {
            "icon": "fa-capsules",
            "title": "Tương tác thuốc huyết áp Amlor",
            "query": "Bệnh nhân tiểu đường vừa cao huyết áp uống Amlor 5mg chung với thuốc gì?"
        }
    ]

    return render_template(
        'rag.html',
        session_id=session_id,
        patient_profile=session_data["patient_profile"],
        quick_prompts=quick_prompts,
        active_tab="rag"
    )

@rag_bp.route('/api/rag/chat', methods=['POST'])
def api_rag_chat():
    """Endpoint Đàm thoại 2 chiều cho Chatbot Y tế Đa lượt"""
    data = request.get_json(force=True) or {}
    message = str(data.get("message", "")).strip()
    session_id: Optional[str] = data.get("session_id")
    user_params: Optional[dict[str, Any]] = data.get("patient_params")

    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống."}), 400

    res = rag_model.chat_medical(
        message=message,
        session_id=session_id,
        user_params=user_params
    )
    return jsonify(res)

@rag_bp.route('/api/rag/reset_session', methods=['POST'])
def api_rag_reset_session():
    """Tạo mới phiên làm việc bệnh án"""
    session_id, session_data = rag_model.get_or_create_session()
    return jsonify({
        "success": True,
        "session_id": session_id,
        "patient_profile": session_data["patient_profile"]
    })

@rag_bp.route('/api/rag/query', methods=['POST'])
def api_rag_query():
    """Endpoint RESTful API tương thích ngược theo chuẩn Tiểu luận Chương 5"""
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
