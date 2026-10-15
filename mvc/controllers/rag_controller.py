# -*- coding: utf-8 -*-
"""
rag_controller.py
Tầng Controller (C) trong kiến trúc MVC cho Hệ thống Trợ lý Y khoa Thông minh GraphRAG Chatbot.
Tích hợp Knowledge Graph (Neo4j) + Dược phẩm Long Châu + Google Gemini 1.5 Flash LLM.
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
    
    # Gợi ý tình huống lâm sàng phong phú (bao gồm bệnh mạn tính & bệnh thông thường)
    quick_prompts = [
        {
            "icon": "fa-pills",
            "title": "Đau đầu uống Panadol",
            "query": "Bị đau đầu uống Panadol hay Hapacol, liều dùng an toàn thế nào?"
        },
        {
            "icon": "fa-fire-flame-curved",
            "title": "Trào ngược dạ dày (GERD)",
            "query": "Bị trào ngược dạ dày ợ chua rát cổ họng nên uống Nexium Mups hay Gaviscon?"
        },
        {
            "icon": "fa-head-side-virus",
            "title": "Cảm sốt & Đau họng",
            "query": "Bị cảm sốt và đau rát họng nên uống thuốc gì an toàn?"
        },
        {
            "icon": "fa-triangle-exclamation",
            "title": "Chống chỉ định Metformin",
            "query": "Người bệnh suy thận nặng có nên tiếp tục uống Metformin không?"
        },
        {
            "icon": "fa-bone",
            "title": "Cơn Gout cấp",
            "query": "Sưng đau khớp ngón chân cái do cơn gút cấp uống Colchicine thế nào?"
        },
        {
            "icon": "fa-shield-virus",
            "title": "Dị ứng & Mề đay",
            "query": "Bị dị ứng thời tiết nổi mề đay mẩn ngứa uống Telfast HD 180mg có an toàn không?"
        },
        {
            "icon": "fa-compass",
            "title": "Chóng mặt tiền đình",
            "query": "Hay bị hoa mắt chóng mặt quay cuồng do rối loạn tiền đình nên uống Betaserc thế nào?"
        },
        {
            "icon": "fa-store",
            "title": "Báo giá Dược phẩm Long Châu",
            "query": "Thuốc Trajenta 5mg và Nexium Mups 20mg giá bao nhiêu ở Long Châu?"
        },
        {
            "icon": "fa-chart-line",
            "title": "Cổ phiếu AMZN (Mục 5.5)",
            "query": "Cổ phiếu Amazon (AMZN) có động lực tăng trưởng gì và đối mặt rủi ro nào theo Form 10-K?"
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
    """Endpoint Đàm thoại 2 chiều cho Chatbot Y tế Đa lượt (Hỗ trợ Tăng cường Gemini 1.5 Flash)"""
    data = request.get_json(force=True) or {}
    message = str(data.get("message", "")).strip()
    session_id: Optional[str] = data.get("session_id")
    user_params: Optional[dict[str, Any]] = data.get("patient_params")
    gemini_api_key: Optional[str] = data.get("gemini_api_key")
    use_llm: bool = data.get("use_llm", True)

    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống."}), 400

    res = rag_model.chat_medical(
        message=message,
        session_id=session_id,
        user_params=user_params,
        gemini_api_key=gemini_api_key,
        use_llm=use_llm
    )
    return jsonify(res)

@rag_bp.route('/api/rag/verify_gemini_key', methods=['POST'])
def api_rag_verify_key():
    """Kiểm tra tính hợp lệ của Gemini API Key"""
    data = request.get_json(force=True) or {}
    key = str(data.get("key", "")).strip()
    if not key:
        return jsonify({"valid": False, "error": "Vui lòng nhập API Key hợp lệ."}), 400

    test_res = rag_model.call_gemini_llm(
        prompt="Xin chào, hãy trả lời đúng 2 từ: Đã kết nối",
        system_instruction="Trả lời cực kỳ ngắn gọn.",
        api_key=key
    )
    if test_res:
        return jsonify({"valid": True, "message": "API Key chính xác! Google Gemini 1.5 Flash đã sẵn sàng hoạt động."})
    else:
        return jsonify({"valid": False, "error": "API Key không chính xác hoặc không thể kết nối đến máy chủ Google AI Studio."}), 400

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

