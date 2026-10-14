# -*- coding: utf-8 -*-
"""
rag_model.py
Tầng Model (M) trong kiến trúc MVC cho Hệ thống Đồ thị Tri thức (Knowledge Graph)
và Trợ lý Y khoa Thông minh GraphRAG Chatbot Đàm thoại Đa lượt.
Hỗ trợ kiến thức chuyên sâu về: Đái tháo đường, Suy thận mạn tính (CKD), Tăng huyết áp, 
Tim mạch, Tương tác thuốc và Chế độ dinh dưỡng lâm sàng.
"""

import time
import re
import uuid
from typing import Any, Optional, Dict, List, Union
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RAGModel:
    def __init__(self):
        # 1. Quản lý phiên đàm thoại đa lượt (Multi-turn Sessions)
        self.sessions = {}

        # 2. Cơ sở tri thức Đồ thị Y tế Mở Rộng Liên Kết Nhà Thuốc Long Châu & Bệnh Viện
        self.medical_graph = {
            "conditions": [
                {"id": "c1", "name": "Đái tháo đường Tuýp 2", "icd10": "E11", "type": "disease", "color": "#ef4444"},
                {"id": "c2", "name": "Suy thận mạn tính Giai đoạn 4-5", "icd10": "N18.4", "type": "disease", "color": "#dc2626"},
                {"id": "c3", "name": "Nhiễm toan Lactic", "icd10": "E87.2", "type": "risk", "color": "#b91c1c"},
                {"id": "c4", "name": "Tăng huyết áp", "icd10": "I10", "type": "disease", "color": "#f97316"},
                {"id": "c5", "name": "Hạ đường huyết cấp tính", "icd10": "E16.2", "type": "risk", "color": "#e11d48"},
                {"id": "c6", "name": "Suy tim (Heart Failure)", "icd10": "I50", "type": "disease", "color": "#ea580c"},
                {"id": "c7", "name": "Bệnh thận đái tháo đường (DKD)", "icd10": "E11.2", "type": "disease", "color": "#991b1b"}
            ],
            "drugs": [
                {"id": "d1", "name": "Metformin", "class": "Biguanide", "dose": "500mg - 1000mg x 2 lần/ngày", "type": "drug", "color": "#10b981"},
                {"id": "d2", "name": "Insulin Glargine", "class": "Hormone", "dose": "10 IU/ngày tiêm dưới da", "type": "drug", "color": "#8b5cf6"},
                {"id": "d3", "name": "Gliclazide", "class": "Sulfonylurea", "dose": "30mg - 120mg/ngày", "type": "drug", "color": "#06b6d4"},
                {"id": "d4", "name": "Linagliptin", "class": "DPP-4 Inhibitor", "dose": "5mg x 1 lần/ngày (không cần chỉnh liều thận)", "type": "drug", "color": "#14b8a6"},
                {"id": "d5", "name": "Dapagliflozin", "class": "SGLT-2 Inhibitor", "dose": "10mg x 1 lần/ngày (bảo vệ tim & thận)", "type": "drug", "color": "#0ea5e9"},
                {"id": "d6", "name": "Amlodipine", "class": "Chẹn Canxi CCB", "dose": "5mg/ngày (hạ huyết áp an toàn)", "type": "drug", "color": "#38bdf8"},
                {"id": "d7", "name": "Perindopril", "class": "Ức chế men chuyển ACEi", "dose": "5mg/ngày (bảo vệ thận sớm)", "type": "drug", "color": "#a855f7"}
            ],
            "pharmacy_brands": [
                {"id": "b1", "name": "Glucophage 500mg", "active": "Metformin", "mfg": "Merck (Pháp)", "price": 4500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b2", "name": "Trajenta 5mg", "active": "Linagliptin", "mfg": "Boehringer (Đức)", "price": 26500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b3", "name": "Lantus SoloStar", "active": "Insulin Glargine", "mfg": "Sanofi (Pháp)", "price": 285000, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b4", "name": "Forxiga 10mg", "active": "Dapagliflozin", "mfg": "AstraZeneca", "price": 28000, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b5", "name": "Diamicron MR 60mg", "active": "Gliclazide", "mfg": "Servier (Pháp)", "price": 4200, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b6", "name": "Amlor 5mg", "active": "Amlodipine", "mfg": "Pfizer (Mỹ)", "price": 8500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b7", "name": "Coversyl 5mg", "active": "Perindopril", "mfg": "Servier (Pháp)", "price": 7900, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b8", "name": "Panadol Extra", "active": "Paracetamol", "mfg": "GSK", "price": 2000, "rx": False, "type": "brand", "color": "#c084fc"}
            ],
            "facilities": [
                {"id": "fac1", "name": "Nhà thuốc Long Châu", "type": "pharmacy", "desc": "Chuỗi 1.800+ nhà thuốc GPP", "color": "#0284c7"},
                {"id": "fac2", "name": "Bệnh viện Đa khoa / BV Thận", "type": "hospital", "desc": "Phác đồ Bộ Y tế & Hội đồng Khoa học", "color": "#475569"}
            ],
            "biomarkers": [
                {"id": "b1", "name": "eGFR < 30 mL/min", "type": "biomarker", "color": "#f59e0b"},
                {"id": "b2", "name": "HbA1c > 8.0%", "type": "biomarker", "color": "#f59e0b"},
                {"id": "b3", "name": "Glucose lúc đói > 13 mmol/L", "type": "biomarker", "color": "#f59e0b"},
                {"id": "b4", "name": "Protein niệu (Đạm nước tiểu)", "type": "biomarker", "color": "#f59e0b"}
            ],
            "relations": [
                # Lâm sàng & Phác đồ
                {"from": "Đái tháo đường Tuýp 2", "to": "Metformin", "rel": "FIRST_LINE_TREATMENT"},
                {"from": "Đái tháo đường Tuýp 2", "to": "Gliclazide", "rel": "ALTERNATIVE_TREATMENT"},
                {"from": "Đái tháo đường Tuýp 2", "to": "Insulin Glargine", "rel": "ADVANCED_TREATMENT"},
                {"from": "Đái tháo đường Tuýp 2", "to": "Linagliptin", "rel": "SAFE_FOR_RENAL"},
                {"from": "Đái tháo đường Tuýp 2", "to": "Dapagliflozin", "rel": "CARDIO_RENAL_PROTECTION"},
                {"from": "Đái tháo đường Tuýp 2", "to": "Bệnh thận đái tháo đường (DKD)", "rel": "NGUYÊN_NHÂN_HÀNG_ĐẦU"},
                {"from": "Tăng huyết áp", "to": "Amlodipine", "rel": "FIRST_LINE_HYPERTENSION"},
                {"from": "Tăng huyết áp", "to": "Perindopril", "rel": "FIRST_LINE_HYPERTENSION"},
                {"from": "Perindopril", "to": "Bệnh thận đái tháo đường (DKD)", "rel": "PROTECTS_RENAL_EARLY"},
                {"from": "Bệnh thận đái tháo đường (DKD)", "to": "Suy thận mạn tính Giai đoạn 4-5", "rel": "TIẾN_TRIỂN_THÀNH"},
                {"from": "Bệnh thận đái tháo đường (DKD)", "to": "Protein niệu (Đạm nước tiểu)", "rel": "DẤU_HIỆU_SỚM"},
                {"from": "Metformin", "to": "Suy thận mạn tính Giai đoạn 4-5", "rel": "CONTRAINDICATED_IN", "severity": "Absolute"},
                {"from": "Metformin", "to": "Nhiễm toan Lactic", "rel": "RISK_OF"},
                {"from": "Metformin", "to": "eGFR < 30 mL/min", "rel": "CONTRAINDICATED_WHEN"},
                {"from": "Gliclazide", "to": "Hạ đường huyết cấp tính", "rel": "RISK_OF"},
                {"from": "Suy thận mạn tính Giai đoạn 4-5", "to": "Linagliptin", "rel": "PREFERRED_DPP4I"},
                {"from": "Suy thận mạn tính Giai đoạn 4-5", "to": "Insulin Glargine", "rel": "PREFERRED_INSULIN"},

                # Liên kết Biệt Dược Long Châu -> Hoạt Chất
                {"from": "Glucophage 500mg", "to": "Metformin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Trajenta 5mg", "to": "Linagliptin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Lantus SoloStar", "to": "Insulin Glargine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Forxiga 10mg", "to": "Dapagliflozin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Diamicron MR 60mg", "to": "Gliclazide", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Amlor 5mg", "to": "Amlodipine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Coversyl 5mg", "to": "Perindopril", "rel": "CHỨA_HOẠT_CHẤT"},

                # Liên kết Biệt Dược -> Nhà thuốc Long Châu
                {"from": "Glucophage 500mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~4.500đ/viên - Rx)"},
                {"from": "Trajenta 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~26.500đ/viên - Rx)"},
                {"from": "Lantus SoloStar", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~285k/bút - Rx)"},
                {"from": "Forxiga 10mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~28.000đ/viên - Rx)"},
                {"from": "Diamicron MR 60mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~4.200đ/viên - Rx)"},
                {"from": "Amlor 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~8.500đ/viên - Rx)"},
                {"from": "Coversyl 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~7.900đ/viên - Rx)"},
                {"from": "Panadol Extra", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~2.000đ/viên - OTC)"},

                # Liên kết Bệnh viện -> Phác đồ
                {"from": "Bệnh viện Đa khoa / BV Thận", "to": "Đái tháo đường Tuýp 2", "rel": "HỘI_CHẨN_CHUYÊN_KHOA"},
                {"from": "Bệnh viện Đa khoa / BV Thận", "to": "Suy thận mạn tính Giai đoạn 4-5", "rel": "PHÁC_ĐỒ_BỘ_Y_TẾ"}
            ]
        }

        # 3. Cơ sở tri thức Đồ thị Tài chính (Financial Knowledge Graph)
        self.financial_graph = {
            "companies": [
                {
                    "ticker": "AMZN",
                    "company_name": "Amazon.com, Inc.",
                    "sector": "E-Commerce & Cloud Computing",
                    "subsidiaries": ["AWS", "Zoox", "Twitch"],
                    "key_competitors": ["Microsoft (MSFT)", "Alphabet (GOOGL)"],
                    "supply_chain_risks": ["Sự thiếu hụt bộ vi xử lý AI GPU", "Chi phí năng lượng trung tâm dữ liệu"]
                }
            ],
            "relations": [
                {"from": "Amazon (AMZN)", "to": "AWS Cloud", "rel": "Sở hữu"},
                {"from": "AWS Cloud", "to": "Nhu cầu Hạ tầng AI", "rel": "Động lực tăng trưởng"},
                {"from": "AWS Cloud", "to": "Thiếu hụt GPU AI", "rel": "Rủi ro cung ứng"},
                {"from": "Amazon (AMZN)", "to": "Microsoft (MSFT)", "rel": "Cạnh tranh trực tiếp"}
            ]
        }

        # 4. Kho tài liệu phác đồ y tế Mở Rộng Chuyên Sâu (Comprehensive Clinical Guidelines Corpus)
        self.medical_guidelines = [
            {
                "id": "DOC001",
                "text": "Metformin là thuốc hạ đường huyết hàng đầu cho bệnh nhân Đái tháo đường Tuýp 2. "
                        "Tuy nhiên, Metformin chống chỉ định tuyệt đối khi eGFR < 30 mL/min/1.73m2 "
                        "(suy thận nặng) do nguy cơ gây tích tụ thuốc dẫn đến nhiễm toan acid lactic nguy hiểm đến tính mạng.",
                "source": "ADA_Standards_of_Care_2026.pdf",
                "page": 45
            },
            {
                "id": "DOC002",
                "text": "Đối với bệnh nhân tiểu đường có tổn thương thận mạn tính tiến triển (eGFR < 30 mL/min), "
                        "cần ngưng ngay Metformin và Sulfonylurea chuyển hóa qua thận. Lựa chọn ưu tiên "
                        "là chuyển sang Insulin nền hoặc thuốc ức chế DPP-4 không thải qua thận như Linagliptin (5mg/ngày).",
                "source": "KDIGO_Diabetes_Management_2026.pdf",
                "page": 12
            },
            {
                "id": "DOC003",
                "text": "Mục tiêu kiểm soát đường huyết: Duy trì HbA1c dưới 7.0% ở phần lớn người trưởng thành. "
                        "Nếu Glucose lúc đói > 13.0 mmol/L và HbA1c > 10.0% kèm triệu chứng sút cân, đa niệu cấp, "
                        "khuyến cáo khởi trị ngay lập tức bằng Insulin tiêm kết hợp theo dõi sát đường huyết mao mạch.",
                "source": "Bo_Y_Te_Huong_Dan_Dieu_Tri_2026.pdf",
                "page": 8
            },
            {
                "id": "DOC004",
                "text": "Thuốc ức chế kênh đồng vận chuyển Natri-Glucose 2 (SGLT-2i như Dapagliflozin, Empagliflozin) "
                        "được khuyến cáo mạnh mẽ cho bệnh nhân ĐTĐ tuýp 2 có kèm suy tim (HFrEF) hoặc bệnh thận mạn tính (CKD) "
                        "nhằm làm chậm tiến triển suy thận và giảm tỷ lệ tử vong do tim mạch.",
                "source": "KDIGO_Cardiovascular_Renal_Protection_2026.pdf",
                "page": 24
            },
            {
                "id": "DOC005",
                "text": "Xử trí Hạ đường huyết (Glucose máu < 3.9 mmol/L): Áp dụng quy tắc số 15 - Uống ngay 15g đường "
                        "nhanh (nước hoa quả, 3 viên đường), nghỉ ngơi 15 phút và kiểm tra lại đường huyết. Nếu vẫn thấp, lặp lại thêm 15g.",
                "source": "ADA_Hypoglycemia_Protocols_2026.pdf",
                "page": 31
            },
            {
                "id": "DOC006",
                "text": "Định nghĩa và Phân loại 5 Giai đoạn Bệnh thận mạn (CKD) theo KDIGO: "
                        "Giai đoạn 1: eGFR >= 90 (chức năng thận bình thường nhưng có tổn thương thận/đạm niệu). "
                        "Giai đoạn 2: eGFR 60-89 (suy giảm nhẹ). "
                        "Giai đoạn 3: eGFR 30-59 (suy giảm trung bình, chia thành 3a và 3b). "
                        "Giai đoạn 4: eGFR 15-29 (suy thận nặng, cần chuẩn bị lọc máu hoặc ghép thận). "
                        "Giai đoạn 5: eGFR < 15 (suy thận giai đoạn cuối, bắt buộc điều trị thay thế thận).",
                "source": "KDIGO_CKD_Evaluation_Management_2026.pdf",
                "page": 16
            },
            {
                "id": "DOC007",
                "text": "Bệnh thận đái tháo đường (Diabetic Kidney Disease - DKD): Là biến chứng vi mạch phổ biến nhất "
                        "của bệnh đái tháo đường, chiếm 40% các trường hợp suy thận mạn giai đoạn cuối. "
                        "Đường huyết tăng cao kéo dài làm xơ hóa cầu thận, xuất hiện protein niệu (nước tiểu có nhiều bọt), "
                        "tăng huyết áp thứ phát và suy giảm dần mức lọc cầu thận eGFR.",
                "source": "Bo_Y_Te_Bien_Chung_Than_DTD_2026.pdf",
                "page": 19
            },
            {
                "id": "DOC008",
                "text": "Nguyên tắc Dinh dưỡng cho Bệnh nhân Suy thận mạn tính (CKD Stages 3-5): "
                        "Hạn chế lượng đạm (protein) từ 0.6 - 0.8 g/kg trọng lượng cơ thể/ngày để giảm tải cho thận. "
                        "Giảm muối (< 2g Natri/ngày tương đương 1 thìa cà phê muối) để kiểm soát huyết áp và chống phù. "
                        "Hạn chế thực phẩm giàu Kali (chuối, cam, nước dừa) và Phosphor (nội tạng, sữa) khi eGFR < 30.",
                "source": "KDIGO_Clinical_Nutrition_in_CKD_2026.pdf",
                "page": 28
            },
            {
                "id": "DOC009",
                "text": "Danh mục Dược phẩm Biệt dược Nhà thuốc Long Châu & Bệnh viện: "
                        "Glucophage (hoạt chất Metformin 500mg/850mg/XR 1000mg) do Merck Santé sản xuất là thuốc kê đơn (Rx), "
                        "đơn giá tham khảo khoảng 4.500đ/viên. Thuốc bắt buộc phải có đơn của bác sĩ điều trị và tuyệt đối không bán "
                        "cho bệnh nhân suy thận nặng eGFR < 30 mL/min do nguy cơ toan hóa lactic. "
                        "Thuốc Trajenta (Linagliptin 5mg) của Boehringer Ingelheim có giá tham khảo khoảng 26.500đ/viên (Rx), "
                        "đây là thuốc ưu tiên hàng đầu tại Long Châu cho người suy thận vì không cần chỉnh liều.",
                "source": "LongChau_Pharmacy_Formulary_2026.pdf",
                "page": 15
            },
            {
                "id": "DOC010",
                "text": "Bút tiêm Lantus SoloStar (Insulin Glargine 100 IU/ml - 3ml) của Sanofi có giá tham khảo khoảng 285.000đ/bút "
                        "tại chuỗi Nhà thuốc Long Châu và khoa Dược bệnh viện. Là thuốc kê đơn (Rx), bảo quản tiêu chuẩn 2-8 độ C trong ngăn mát. "
                        "Dùng tiêm dưới da 1 lần mỗi tối cho bệnh nhân đái tháo đường kèm suy thận mạn tiến triển khi các thuốc uống bị chống chỉ định.",
                "source": "LongChau_ColdChain_Insulin_Guide_2026.pdf",
                "page": 7
            },
            {
                "id": "DOC011",
                "text": "Thuốc ức chế SGLT-2 Forxiga (Dapagliflozin 10mg - AstraZeneca) có giá tham khảo 28.000đ/viên (Rx) tại Long Châu. "
                        "Thuốc được chỉ định phối hợp để bảo vệ tim mạch và làm chậm suy thận. Tuy nhiên khi mức lọc cầu thận eGFR < 20 - 25 mL/min, "
                        "hiệu quả hạ đường huyết của thuốc giảm sút và cần hội chẩn bác sĩ chuyên khoa thận.",
                "source": "AstraZeneca_Forxiga_Clinical_Monograph_2026.pdf",
                "page": 22
            },
            {
                "id": "DOC012",
                "text": "Tương tác thuốc điều trị Tăng huyết áp và Đái tháo đường: "
                        "Bệnh nhân đái tháo đường thường phối hợp Amlor 5mg (Amlodipine, giá ~8.500đ/viên tại Long Châu) "
                        "hoặc Coversyl 5mg (Perindopril, giá ~7.900đ/viên). Amlodipine đào thải qua gan nên an toàn khi suy thận. "
                        "Perindopril giúp bảo vệ thận ở giai đoạn sớm có đạm niệu nhưng khi suy thận nặng (eGFR < 30) cần theo dõi sát "
                        "nồng độ Kali máu và Creatinine huyết thanh để phòng nguy cơ tăng kali máu nguy hiểm.",
                "source": "Bo_Y_Te_Tuong_Tac_Thuoc_Lam_Sang_2026.pdf",
                "page": 34
            }
        ]

        # 5. Kho báo cáo tài chính Form 10-K
        self.financial_reports = [
            {
                "id": "FIN001",
                "ticker": "AMZN",
                "report_type": "Form 10-K Q4",
                "year": 2026,
                "text": "Bộ phận điện toán đám mây Amazon Web Services (AWS) ghi nhận mức tăng trưởng doanh thu 19% "
                        "đạt 27.5 tỷ USD trong quý nhờ nhu cầu triển khai hạ tầng AI tạo sinh bùng nổ. "
                        "Tuy nhiên, chi phí đầu tư cơ sở hạ tầng (CapEx) tăng mạnh do mở rộng trung tâm dữ liệu.",
                "source": "Amazon_Form_10K_Annual_Report_2026.pdf",
                "page": 28
            },
            {
                "id": "FIN002",
                "ticker": "AMZN",
                "report_type": "Form 10-K Q3",
                "year": 2025,
                "text": "Rủi ro chuỗi cung ứng phần cứng AI: Sự phụ thuộc lớn vào các nhà cung ứng chip tăng tốc độc quyền "
                        "có thể dẫn đến chậm trễ bàn giao cụm tính toán đám mây thế hệ mới và gia tăng chi phí biên.",
                "source": "Amazon_Form_10K_Supply_Chain_Risk_2025.pdf",
                "page": 41
            }
        ]

        self._init_vector_indices()

    def _init_vector_indices(self):
        # Y tế
        self.med_vectorizer = TfidfVectorizer()
        med_docs = [d["text"] for d in self.medical_guidelines]
        self.med_vectors = self.med_vectorizer.fit_transform(med_docs)

        # Tài chính
        self.fin_vectorizer = TfidfVectorizer()
        fin_docs = [d["text"] for d in self.financial_reports]
        self.fin_vectors = self.fin_vectorizer.fit_transform(fin_docs)

    # =========================================================================
    # QUẢN LÝ BỘ NHỚ ĐÀM THOẠI ĐA LƯỢT (MULTI-TURN CHAT SESSIONS)
    # =========================================================================
    def get_or_create_session(self, session_id=None):
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())[:8]
            self.sessions[session_id] = {
                "created_at": time.time(),
                "patient_profile": {
                    "age": 55,
                    "gender": "Nam",
                    "egfr": 25,
                    "hba1c": 8.5,
                    "fasting_glucose": 9.2,
                    "conditions": ["Đái tháo đường Tuýp 2", "Suy thận mạn tính Giai đoạn 4"],
                    "medications": ["Metformin"]
                },
                "history": []
            }
        return session_id, self.sessions[session_id]

    def update_patient_profile_from_text(self, profile, text):
        """Tự động trích xuất các chỉ số xét nghiệm và bệnh lý từ ngôn ngữ tự nhiên"""
        t = text.lower()
        
        # eGFR
        egfr_match = re.search(r'egfr\s*(?:là|:|=|\s+)?\s*([0-9]{1,3})', t)
        if egfr_match:
            profile["egfr"] = int(egfr_match.group(1))

        # HbA1c
        hba1c_match = re.search(r'hba1c\s*(?:là|:|=|\s+)?\s*([0-9]+(?:\.[0-9]+)?)', t)
        if hba1c_match:
            profile["hba1c"] = float(hba1c_match.group(1))

        # Tuổi
        age_match = re.search(r'([0-9]{1,2})\s*tuổi', t)
        if age_match:
            profile["age"] = int(age_match.group(1))

        # Bệnh lý
        if "suy thận" in t or "thận mạn" in t:
            if "Suy thận mạn tính Giai đoạn 4" not in profile["conditions"]:
                profile["conditions"].append("Suy thận mạn tính Giai đoạn 4")
        if "suy tim" in t:
            if "Suy tim" not in profile["conditions"]:
                profile["conditions"].append("Suy tim")
        if "huyết áp" in t or "tăng huyết áp" in t:
            if "Tăng huyết áp" not in profile["conditions"]:
                profile["conditions"].append("Tăng huyết áp")

        # Thuốc đề cập
        for drug in ["metformin", "insulin", "gliclazide", "linagliptin", "dapagliflozin"]:
            if drug in t and drug.capitalize() not in profile["medications"]:
                profile["medications"].append(drug.capitalize())

        return profile

    # =========================================================================
    # CORE REASONING: CHATBOT ĐÀM THOẠI Y KHOA THÔNG MINH
    # =========================================================================
    def chat_medical(self, message: str, session_id: Optional[str] = None, user_params: Optional[dict[str, Any]] = None):
        t0 = time.time()
        session_id, session = self.get_or_create_session(session_id)
        profile = session["patient_profile"]

        # Cập nhật nếu người dùng truyền trực tiếp qua widget
        if user_params:
            for k, v in user_params.items():
                if v is not None:
                    profile[k] = v

        # Phân tích thực thể từ tin nhắn người dùng
        profile = self.update_patient_profile_from_text(profile, message)

        # 1. Truy xuất Vector các phân mảnh phác đồ liên quan
        q_vec = self.med_vectorizer.transform([message])
        sims = cosine_similarity(q_vec, self.med_vectors)[0]
        ranked_idx = np.argsort(sims)[::-1][:3]
        
        evidence_sources = []
        for idx in ranked_idx:
            doc = self.medical_guidelines[idx]
            evidence_sources.append({
                "doc_id": doc["id"],
                "source": doc["source"],
                "page": doc["page"],
                "snippet": doc["text"],
                "similarity": round(float(sims[idx]), 4)
            })

        # 2. Phân loại Ý định (Clinical Intent Recognition) & Suy luận Đồ thị Tri thức
        msg_lower = message.lower()
        egfr = profile.get("egfr", 25)
        hba1c = profile.get("hba1c", 8.5)
        
        highlight_nodes = ["Bệnh nhân (Pima)"]
        suggested_followups = []
        triage_level = "info" # info, warning, danger

        # =====================================================================
        # PHÂN TÍCH Ý ĐỊNH CHUYÊN SÂU
        # =====================================================================
        is_asking_metformin_contraindication = (
            ("metformin" in msg_lower or "thuốc hạ đường" in msg_lower) and
            (egfr < 30 or "suy thận" in msg_lower or "egfr" in msg_lower or "thận" in msg_lower or "chống chỉ định" in msg_lower or "uống được" in msg_lower or "tiếp tục dùng" in msg_lower)
        )
        is_asking_diet = any(term in msg_lower for term in [
            "chế độ ăn", "ăn gì", "kiêng gì", "dinh dưỡng", "thực đơn", "uống nước", "muối", "đạm", "protein"
        ])
        is_asking_general_symptom = any(term in msg_lower for term in [
            "đau họng", "rát họng", "viêm họng", "cảm sốt", "nhức đầu", 
            "đau đầu", "đau cơ", "mỏi cơ", "đau người", "vận động mạnh", "thuốc giảm đau"
        ])
        is_asking_hospital = any(term in msg_lower for term in [
            "bệnh viện", "khoa thận", "khám ở đâu", "tuyến trên", "bạch mai", 
            "chợ rẫy", "nội tiết trung ương", "đại học y dược", "bác sĩ chuyên khoa"
        ])
        is_asking_interaction = any(term in msg_lower for term in [
            "tương tác", "uống chung", "dùng chung", "phối hợp", "kết hợp thuốc", "uống cùng lúc", 
            "huyết áp và tiểu đường", "uống với"
        ]) or (("amlor" in msg_lower or "coversyl" in msg_lower) and ("thuốc gì" in msg_lower or "an toàn" in msg_lower or "với" in msg_lower))
        is_asking_brand_drug = any(term in msg_lower for term in [
            "long châu", "biệt dược", "glucophage", "trajenta", "lantus", "forxiga", 
            "diamicron", "amlor", "coversyl", "panadol", "giá thuốc", "bao nhiêu tiền", 
            "mua ở đâu", "nhà thuốc", "kê đơn", "rx", "otc", "đắt không", "hộp bao nhiêu"
        ])
        is_asking_kidney_disease = (
            any(term in msg_lower for term in [
                "suy thận", "bệnh thận", "thận mạn", "thận yếu", "chức năng thận", 
                "chạy thận", "lọc máu", "creatinine", "protein niệu", "đạm niệu", "nước tiểu có bọt", "egfr"
            ]) and not is_asking_brand_drug and not is_asking_hospital and not is_asking_interaction and not is_asking_general_symptom
        )
        is_asking_diabetes_overview = (
            any(term in msg_lower for term in [
                "tiểu đường là gì", "đái tháo đường là gì", "nói về bệnh tiểu đường", 
                "tìm hiểu về tiểu đường", "thế nào là tiểu đường", "tiểu đường tuýp 2 là gì", 
                "bệnh tiểu đường", "bệnh đái tháo đường", "tiểu đường tuýp 2", "tiểu đường", "đái tháo đường"
            ]) and not is_asking_metformin_contraindication 
               and not is_asking_diet 
               and not is_asking_kidney_disease 
               and not is_asking_brand_drug 
               and not is_asking_hospital 
               and not is_asking_interaction
               and not is_asking_general_symptom
        )

        # Ưu tiên 1: Chống chỉ định Metformin khi suy thận (eGFR < 30)
        if is_asking_metformin_contraindication:
            triage_level = "danger"
            decision_title = "CẢNH BÁO: CHỐNG CHỈ ĐỊNH TUYỆT ĐỐI METFORMIN KHI SUY THẬN"
            reply_text = (
                f"Với chỉ số **eGFR = {egfr} mL/min/1.73m²**, bệnh nhân đã rơi vào **Suy thận mạn tính Giai đoạn 4 (Suy thận nặng)**.\n\n"
                "**1. Khuyến cáo khẩn cấp:**\n"
                "• **NGƯNG NGAY METFORMIN:** Thuốc bị chống chỉ định tuyệt đối khi eGFR < 30 mL/min do thận không còn khả năng "
                "đào thải, dẫn tới tích tụ thuốc gây biến chứng **Nhiễm toan Lactic (Lactic Acidosis)** với tỷ lệ tử vong lên tới 50%.\n\n"
                "**2. Phác đồ thay thế an toàn được khuyến nghị:**\n"
                "• **Lựa chọn 1 (Ưu tiên số 1):** Chuyển sang **Insulin nền (Insulin Glargine)** tiêm dưới da 1 lần/ngày. "
                "Insulin đào thải qua gan, hoàn toàn an toàn cho người suy thận.\n"
                "• **Lựa chọn 2:** Dùng thuốc ức chế DPP-4 **Linagliptin 5mg/ngày** (thuốc duy nhất trong nhóm đào thải qua đường mật/gan, "
                "không cần hiệu chỉnh liều khi suy thận).\n\n"
                "*(Căn cứ theo Hướng dẫn Phân loại Bệnh thận KDIGO 2026 - Trang 12 và Tiêu chuẩn Điều trị ADA 2026 - Trang 45)*"
            )
            reasoning_path = "Bệnh nhân -> eGFR < 30 (Suy thận GĐ 4) -> CONTRAINDICATED_IN -> Metformin -> PREFERRED -> Insulin Glargine / Linagliptin"
            highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Metformin", "Nhiễm toan Lactic", "Insulin Glargine", "Linagliptin", "eGFR < 30 mL/min"])
            suggested_followups = [
                "Liều dùng khởi đầu của Insulin Glargine là bao nhiêu?",
                "Thuốc Linagliptin 5mg có tác dụng phụ gì không?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?"
            ]

        # Ưu tiên 2: Chế độ ăn & Dinh dưỡng
        elif is_asking_diet:
            triage_level = "info"
            decision_title = "HƯỚNG DẪN DINH DƯỠNG: TIỂU ĐƯỜNG KÈM SUY THẬN MẠN TÍNH"
            reply_text = (
                f"Chế độ ăn cho bệnh nhân **Đái tháo đường kèm Suy thận mạn Giai đoạn 4 (eGFR = {egfr} mL/min)** cần tuân thủ nghiêm ngặt "
                "để bảo tồn chức năng thận còn lại và kiểm soát đường huyết:\n\n"
                "**1. Kiểm soát Lượng Đạm (Protein):**\n"
                "• Hạn chế lượng đạm xuống **0.6 - 0.8 g/kg cân nặng/ngày** (ví dụ bệnh nhân 60kg chỉ nên ăn khoảng 36 - 48g protein/ngày).\n"
                "• Ưu tiên đạm giá trị sinh học cao: Lòng trắng trứng, thịt ức gà nạc, cá nước ngọt. Giảm thịt bò, thịt đỏ.\n\n"
                "**2. Giảm Muối (Natri):**\n"
                "• Ăn nhạt hoàn toàn: Dưới **2g Natri/ngày** (tương đương dưới 1 thìa cà phê muối tinh 5g). Không chấm nước mắm nguyên chất.\n"
                "• Tránh thực phẩm chế biến sẵn: Xúc xích, thịt xông khói, đồ hộp, mì tôm.\n\n"
                "**3. Kiểm soát Kali và Phosphor (Rất quan trọng khi eGFR < 30):**\n"
                "• Tránh quả giàu Kali: Chuối, cam, nho khô, bơ, nước dừa (nguy cơ ngừng tim do tăng kali máu).\n"
                "• Tránh thực phẩm giàu Phosphor: Nội tạng động vật, phô mai, lòng đỏ trứng, nước ngọt có ga sẫm màu.\n\n"
                "**4. Lượng Nước Uống:**\n"
                "• Uống lượng nước bằng: *Lượng nước tiểu 24h + 500 mL* (tránh thừa nước gây phù phổi cấp)."
            )
            reasoning_path = "Bệnh nhân -> Suy thận mạn GĐ 4 -> NGUYÊN TẮC DINH DƯỠNG -> Hạn chế Protein (0.6-0.8g/kg) & Giảm Natri/Kali"
            highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Bệnh nhân (Pima)"])
            suggested_followups = [
                "Thực đơn mẫu 1 ngày cho người suy thận?",
                "Có được uống sữa dành riêng cho người tiểu đường không?",
                "Tại sao người suy thận phải kiêng chuối và cam?"
            ]

        # Phân nhánh 1.2: Kiến thức tổng quan và chuyên sâu về BỆNH SUY THẬN (CKD)
        elif is_asking_kidney_disease:
            triage_level = "warning" if egfr < 30 else "info"
            decision_title = "TƯ VẤN CHUYÊN SÂU: BỆNH SUY THẬN MẠN TÍNH (CKD) & BIẾN CHỨNG ĐÁI THÁO ĐƯỜNG"
            reply_text = (
                "**Bệnh suy thận (đặc biệt là Suy thận mạn tính - CKD)** là tình trạng suy giảm dần dần và không hồi phục "
                "chức năng lọc các chất cặn bã và nước dư thừa của thận ra khỏi cơ thể.\n\n"
                "**1. Phân loại 5 Giai đoạn Suy thận theo Mức lọc cầu thận (eGFR - KDIGO):**\n"
                "• **Giai đoạn 1 (eGFR $\\ge$ 90 mL/min):** Thận bình thường nhưng đã có tổn thương vi thể (như xuất hiện Protein trong nước tiểu).\n"
                "• **Giai đoạn 2 (eGFR 60 - 89 mL/min):** Suy giảm chức năng thận mức độ nhẹ.\n"
                "• **Giai đoạn 3 (eGFR 30 - 59 mL/min):** Suy giảm trung bình (chia làm 3a: 45-59 và 3b: 30-44). Cần chỉnh liều nhiều loại thuốc.\n"
                f"• **Giai đoạn 4 (eGFR 15 - 29 mL/min):** **Suy thận nặng** ⚠️ *(Chỉ số eGFR của bệnh nhân hiện tại là **{egfr} mL/min** thuộc giai đoạn này)*. Cần chuẩn bị phương án điều trị thay thế thận.\n"
                "• **Giai đoạn 5 (eGFR < 15 mL/min):** **Suy thận giai đoạn cuối**. Bắt buộc phải chạy thận nhân tạo, lọc màng bụng hoặc ghép thận để duy trì sự sống.\n\n"
                "**2. Mối liên hệ mật thiết giữa Tiểu đường và Suy thận:**\n"
                "• Đái tháo đường là **nguyên nhân hàng đầu (chiếm 40 - 50%)** gây suy thận mạn tính trên toàn cầu (**Bệnh thận đái tháo đường - DKD**).\n"
                "• Đường huyết cao kéo dài phá hủy các vi mạch cầu thận, làm tổn thương màng lọc khiến protein thoát ra ngoài nước tiểu.\n\n"
                "**3. Dấu hiệu cảnh báo suy thận:**\n"
                "• Nước tiểu sủi bọt lâu tan (dấu hiệu đạm niệu).\n"
                "• Phù mắt cá chân, bàn chân hoặc phù mi mắt vào buổi sáng.\n"
                "• Tiểu đêm nhiều lần, mệt mỏi, da xanh xao (do thiếu máu thiếu Erythropoietin).\n"
                "• Huyết áp tăng vọt khó kiểm soát."
            )
            reasoning_path = "Đái tháo đường Tuýp 2 -> NGUYÊN NHÂN HÀNG ĐẦU -> Bệnh thận đái tháo đường (DKD) -> TIẾN TRIỂN -> Suy thận mạn tính Giai đoạn 4-5"
            highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Bệnh thận đái tháo đường (DKD)", "Protein niệu (Đạm nước tiểu)", "eGFR < 30 mL/min", "Đái tháo đường Tuýp 2"])
            suggested_followups = [
                "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Suy thận mạn tính giai đoạn 4 có chữa khỏi hoàn toàn được không?"
            ]

        # Phân nhánh 1.3: Tổng quan chuyên sâu về BỆNH ĐÁI THÁO ĐƯỜNG (TIỂU ĐƯỜNG TUÝP 2)
        elif is_asking_diabetes_overview:
            triage_level = "info"
            decision_title = "TỔNG QUAN Y KHOA: BỆNH ĐÁI THÁO ĐƯỜNG TUÝP 2 (TRIỆU CHỨNG, CHẨN ĐOÁN & BIẾN CHỨNG)"
            reply_text = (
                "**Bệnh Đái tháo đường (đặc biệt là Đái tháo đường Tuýp 2)** là một bệnh rối loạn chuyển hóa mạn tính, "
                "đặc trưng bởi tình trạng lượng đường (glucose) trong máu luôn ở mức cao hơn bình thường do cơ thể bị "
                "**đề kháng insulin** kết hợp với suy giảm dần khả năng tiết insulin của tế bào beta tuyến tụy.\n\n"
                "**1. Triệu chứng nhận biết điển hình (Hội chứng \"4 nhiều\"):**\n"
                "• **Ăn nhiều (Đa thực):** Tế bào không hấp thu được glucose để tạo năng lượng, cơ thể liên tục phát tín hiệu đói cồn cào.\n"
                "• **Uống nhiều (Đa ẩm):** Nồng độ đường trong máu cao làm tăng áp lực thẩm thấu, hút nước từ các mô, gây khát nước liên tục, khô miệng.\n"
                "• **Tiểu nhiều (Đa niệu):** Thận vượt ngưỡng tái hấp thu glucose (thường > 10 mmol/L), đường thoát ra nước tiểu kéo theo lượng lớn nước.\n"
                "• **Gầy sút cân nhanh:** Cơ thể không sử dụng được đường nên buộc phải phân giải mô mỡ và cơ bắp để duy trì năng lượng sống.\n\n"
                "**2. Tiêu chuẩn chẩn đoán xác định (Theo Hiệp hội ADA & Bộ Y tế):**\n"
                "• **Glucose máu lúc đói:** $\\ge$ 7.0 mmol/L (126 mg/dL) sau nhịn ăn ít nhất 8 tiếng.\n"
                f"• **HbA1c (Đường huyết trung bình 3 tháng):** $\\ge$ 6.5% *(Chỉ số hiện tại của bệnh nhân là **HbA1c = {hba1c}%**, đang ở mức kiểm soát kém)*.\n"
                "• **Nghiệm pháp dung nạp Glucose 2h:** $\\ge$ 11.1 mmol/L (200 mg/dL).\n"
                "• **Glucose máu bất kỳ:** $\\ge$ 11.1 mmol/L kèm các triệu chứng kinh điển ở trên.\n\n"
                "**3. Các biến chứng mạn tính nguy hiểm:**\n"
                f"• **Bệnh thận đái tháo đường (DKD):** Biến chứng vi mạch phá hủy cầu thận *(bệnh nhân hiện tại đã biến chứng Suy thận Giai đoạn 4, eGFR = {egfr} mL/min)*.\n"
                "• **Bệnh võng mạc tiểu đường:** Gây xuất huyết đáy mắt, phù hoàng điểm, đục thủy tinh thể, nguy cơ mù lòa.\n"
                "• **Bệnh tim mạch & xơ vữa:** Tăng 2 - 4 lần nguy cơ nhồi máu cơ tim và đột quỵ não.\n"
                "• **Bệnh thần kinh & Bàn chân tiểu đường:** Tê bì dị cảm đầu chi, mất cảm giác đau, loét bàn chân khó lành dẫn đến nguy cơ cắt cụt chi.\n\n"
                "**4. Chiến lược điều trị toàn diện:** Kết hợp kiềng 3 chân: Chế độ ăn giảm tinh bột hấp thu nhanh + Luyện tập thể lực 150 phút/tuần + Dùng thuốc cá thể hóa (đặc biệt lưu ý chức năng thận)."
            )
            reasoning_path = "Đái tháo đường Tuýp 2 -> RỐI LOẠN CHUYỂN HÓA -> Đề kháng Insulin & Tăng đường huyết mạn -> BIẾN CHỨNG -> Thận (DKD) & Tim mạch"
            highlight_nodes.extend(["Đái tháo đường Tuýp 2", "HbA1c > 8.0%", "Glucose lúc đói > 13 mmol/L", "Bệnh thận đái tháo đường (DKD)", "Bệnh nhân (Pima)"])
            suggested_followups = [
                "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Dấu hiệu cảnh báo sớm bệnh suy thận ở người tiểu đường là gì?"
            ]

        # =====================================================================
        # NHÁNH 2: HẠ ĐƯỜNG HUYẾT CẤP TÍNH (HYPOGLYCEMIA)
        # =====================================================================
        elif any(term in msg_lower for term in ["hạ đường", "chóng mặt", "vã mồ hôi", "run tay", "đường huyết thấp", "< 3.9", "tụt đường"]):
            triage_level = "warning"
            decision_title = "HƯỚNG DẪN XỬ TRÍ HẠ ĐƯỜNG HUYẾT CẤP TÍNH (QUY TẮC SỐ 15)"
            reply_text = (
                "**Bệnh nhân có dấu hiệu Hạ đường huyết cấp tính (Glucose máu < 3.9 mmol/L). Hãy thực hiện ngay:**\n\n"
                "**Áp dụng Quy tắc số 15 của Hiệp hội Đái tháo đường Hoa Kỳ (ADA):**\n"
                "1. **Bổ sung ngay 15g Carbohydrate hấp thu nhanh:**\n"
                "   • Uống 1/2 cốc nước ép trái cây (cam, táo) hoặc nước ngọt có đường (120ml).\n"
                "   • Hoặc uống 1 cốc nước ấm pha 3 thìa đường / 1 gói mật ong.\n"
                "   • Hoặc ăn 3 - 4 viên kẹo ngọt.\n"
                "2. **Nghỉ ngơi 15 phút:** Tiến hành đo lại đường huyết mao mạch bằng máy đo cá nhân.\n"
                "3. **Nếu đường huyết vẫn < 3.9 mmol/L:** Tiếp tục nạp thêm 15g đường và đo lại sau 15 phút.\n"
                "4. Khi đường huyết đã ổn định (> 4.0 mmol/L), hãy cho bệnh nhân ăn bữa phụ (bánh quy, sữa chua hoặc bữa chính) để tránh nguy cơ tái tụt đường huyết."
            )
            reasoning_path = "Bệnh nhân -> Hạ đường huyết cấp tính -> ÁP DỤNG -> Quy tắc 15g Carbonhydrate"
            highlight_nodes.extend(["Hạ đường huyết cấp tính", "Gliclazide"])
            suggested_followups = [
                "Thuốc nào trong đơn gây hạ đường huyết?",
                "Làm sao phòng ngừa hạ đường huyết ban đêm?",
                "Khi nào cần gọi cấp cứu 115?"
            ]

        # =====================================================================
        # NHÁNH 3: TRIỆU CHỨNG ĐAU HỌNG, ĐAU CƠ SAU VẬN ĐỘNG & THUỐC GIẢM ĐAU
        # =====================================================================
        elif is_asking_general_symptom:
            triage_level = "warning" if egfr < 30 else "info"
            decision_title = "TƯ VẤN LÂM SÀNG: ĐAU HỌNG, ĐAU CƠ SAU VẬN ĐỘNG & THUỐC GIẢM ĐAU AN TOÀN"
            reply_text = (
                "**1. Phân tích nguyên nhân đau họng sau khi vận động mạnh:**\n"
                "• Khi bạn tập luyện thể dục thể thao hoặc vận động cường độ cao, cơ thể phải thở dốc chủ yếu bằng đường miệng. "
                "Không khí đi thẳng vào họng mà không được lọc, làm ấm và tạo ẩm qua đường mũi, khiến **niêm mạc họng bị khô rát, xung huyết và kích ứng cơ học**.\n"
                "• Ngoài ra, nếu ra nhiều mồ hôi gặp gió quạt/điều hòa lạnh hoặc uống nước đá lạnh ngay sau tập cũng làm tăng nguy cơ viêm họng cấp.\n\n"
                "**2. Thuốc Giảm Đau An Toàn Được Phép Sử Dụng:**\n"
                "• **Lựa chọn an toàn duy nhất:** **Paracetamol (Panadol Extra / Hapacol 500mg)**: Uống 1 viên khi đau nhiều, cách mỗi 4 - 6 giờ "
                "(tổng liều tối đa không quá 2000mg/ngày). Paracetamol chuyển hóa chủ yếu qua gan nên an toàn cho người bệnh thận.\n\n"
                f"⚠️ **CẢNH BÁO TỐI KHẨN CẤP CHO BỆNH NHÂN (eGFR = {egfr} mL/min):**\n"
                "• **TUYỆT ĐỐI CẤM DÙNG CÁC THUỐC GIẢM ĐAU KHÁNG VIÊM NSAID:** Không được mua hay uống các thuốc như **Ibuprofen, Meloxicam, "
                "Diclofenac (Voltaren), Alaxan, Mobic, Aspirin**.\n"
                "• **Cơ chế nguy hại đến tính mạng:** Nhóm NSAID ức chế enzym Prostaglandin, làm co thắt động mạch đến của cầu thận, cắt đứt lưu lượng máu đến thận. "
                "Bệnh nhân vốn đã ở **Suy thận mạn Giai đoạn 4** nếu uống NSAID sẽ bị **Suy thận cấp vô niệu**, đẩy nhanh tiến trình phải chạy thận nhân tạo ngay lập tức!\n\n"
                "**3. Biện pháp hồi phục tự nhiên không dùng thuốc:**\n"
                "• Súc họng bằng **nước muối sinh lý 0.9% ấm** 3 - 4 lần mỗi ngày.\n"
                "• Uống từng ngụm nước ấm nhỏ để làm ẩm niêm mạc họng, có thể ngậm kẹo thảo dược hoặc chanh mật ong ấm.\n"
                "• Nghỉ ngơi thả lỏng cơ bắp, tránh gắng sức trong 24 - 48 giờ."
            )
            reasoning_path = "Đau họng / Đau cơ do vận động -> Paracetamol (An toàn qua gan) -> CẤM TUYỆT ĐỐI NSAID (Ibuprofen) khi eGFR < 30"
            highlight_nodes.extend(["Panadol Extra", "Suy thận mạn tính Giai đoạn 4-5", "Bệnh nhân (Pima)"])
            suggested_followups = [
                "Tại sao người suy thận không được uống thuốc giảm đau Ibuprofen?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?"
            ]


        # =====================================================================
        # NHÁNH 4: CÁC THUỐC CỤ THỂ (INSULIN, LINAGLIPTIN, DAPAGLIFLOZIN, GLICLAZIDE)
        # =====================================================================
        elif any(term in msg_lower for term in ["insulin", "tiêm", "glargine", "linagliptin", "dapagliflozin", "gliclazide", "sglt2", "dpp4"]):
            triage_level = "info"
            if "insulin" in msg_lower or "glargine" in msg_lower:
                decision_title = "PHÁC ĐỒ SỬ DỤNG INSULIN NỀN CHO BỆNH NHÂN SUY THẬN"
                reply_text = (
                    "**Insulin Glargine (Lantus / Toujeo)** là liệu pháp thay thế tối ưu hàng đầu khi bệnh nhân có suy giảm chức năng thận nặng:\n\n"
                    "• **Liều khởi đầu khuyến nghị:** Thường bắt đầu với **10 IU/ngày** (hoặc 0.1 - 0.2 IU/kg/ngày) tiêm dưới da vào một giờ cố định mỗi tối.\n"
                    "• **Lưu ý đặc biệt khi suy thận:** Khi chức năng thận giảm, sự giáng hóa insulin nội sinh và ngoại sinh cũng giảm, "
                    "làm kéo dài thời gian bán hủy của Insulin. Do đó, cần theo dõi sát để tránh nguy cơ hạ đường huyết ban đêm.\n"
                    "• **Vị trí tiêm:** Vùng bụng (cách rốn 2 đốt ngón tay), mặt trước đùi hoặc mặt sau bắp tay. Luân chuyển vị trí tiêm tránh loạn dưỡng mỡ."
                )
                reasoning_path = "Bệnh nhân -> Suy thận nặng -> THAY THẾ AN TOÀN -> Insulin Glargine"
                highlight_nodes.extend(["Insulin Glargine", "Suy thận mạn tính Giai đoạn 4-5"])
            elif "linagliptin" in msg_lower:
                decision_title = "THUỐC ỨC CHẾ DPP-4 LINAGLIPTIN (TRAJENTA 5MG)"
                reply_text = (
                    "**Linagliptin (Trajenta 5mg)** là một trong những lựa chọn thuốc uống an toàn và tiện lợi nhất cho người bệnh thận:\n\n"
                    "• **Cơ chế:** Ức chế enzym DPP-4, làm tăng nồng độ GLP-1 nội sinh, kích thích tụy tiết insulin khi có thức ăn.\n"
                    "• **Đặc tính độc nhất:** Khoảng 95% thuốc được đào thải qua đường mật và phân, chỉ có 5% qua thận.\n"
                    "• **Liều dùng:** Duy trì cố định **5mg x 1 lần/ngày** ở MỌI giai đoạn suy thận (kể cả bệnh nhân đang chạy thận) mà không cần giảm liều.\n"
                    "• **Nguy cơ hạ đường huyết:** Rất thấp khi dùng đơn độc."
                )
                reasoning_path = "Bệnh nhân -> Suy thận nặng -> THUỐC UỐNG AN TOÀN -> Linagliptin (5mg)"
                highlight_nodes.extend(["Linagliptin", "Suy thận mạn tính Giai đoạn 4-5"])
            else:
                decision_title = "NHÓM THUỐC BẢO VỆ TIM - THẬN SGLT-2i (DAPAGLIFLOZIN)"
                reply_text = (
                    "**Dapagliflozin (Forxiga 10mg)** thuộc nhóm thuốc ức chế SGLT-2 với nhiều đột phá y khoa:\n\n"
                    "• **Cơ chế:** Ức chế tái hấp thu glucose ở ống lượn gần của thận, giúp thải đường thừa qua nước tiểu.\n"
                    "• **Lợi ích lâm sàng:** Đã được chứng minh qua thử nghiệm DAPA-CKD giúp giảm 39% nguy cơ suy thận tiến triển và giảm 31% tử vong do tim mạch.\n"
                    f"• **Lưu ý theo eGFR:** Thuốc có thể dùng để bảo vệ thận khi eGFR >= 20 mL/min. Tuy nhiên hiệu quả hạ đường huyết của thuốc sẽ giảm khi eGFR < 45."
                )
                reasoning_path = "Bệnh nhân -> Đái tháo đường -> BẢO VỆ TIM THẬN -> Dapagliflozin (SGLT-2i)"
                highlight_nodes.extend(["Dapagliflozin", "Suy tim (Heart Failure)"])
            suggested_followups = [
                "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                "Thuốc Linagliptin 5mg có đắt không và uống vào lúc nào?",
                "Cách theo dõi đường huyết khi tiêm Insulin?"
            ]

        # =====================================================================
        # NHÁNH 5: MỤC TIÊU ĐƯỜNG HUYẾT & HBA1C
        # =====================================================================
        elif any(term in msg_lower for term in ["mục tiêu", "hba1c", "glucose đói", "đường huyết bao nhiêu", "chỉ số bình thường"]):
            triage_level = "info"
            decision_title = "MỤC TIÊU KIỂM SOÁT ĐƯỜNG HUYẾT VÀ HBA1C"
            reply_text = (
                f"**Mục tiêu điều trị khuyến cáo cho bệnh nhân (Hiện tại HbA1c: {hba1c}%, Glucose: {profile.get('fasting_glucose', 9.2)} mmol/L):**\n\n"
                "• **HbA1c mục tiêu:** Thường dưới **7.0%** đối với người trưởng thành khỏe mạnh. "
                "Tuy nhiên, ở bệnh nhân có **Suy thận mạn Giai đoạn 4**, mục tiêu HbA1c nên nới lỏng ở mức **7.5% - 8.0%** "
                "nhằm tránh tuyệt đối nguy cơ hạ đường huyết nguy hiểm tính mạng.\n"
                "• **Đường huyết lúc đói:** Duy trì từ **5.0 - 7.2 mmol/L** (90 - 130 mg/dL).\n"
                "• **Đường huyết 2 giờ sau ăn:** Dưới **10.0 mmol/L** (< 180 mg/dL).\n"
                "• **Tần suất xét nghiệm:** Đo HbA1c định kỳ 3 tháng/lần và kiểm tra chức năng thận eGFR định kỳ 1 - 3 tháng/lần."
            )
            reasoning_path = "Bệnh nhân -> HbA1c = 8.5% -> MỤC TIÊU ĐIỀU TRỊ -> HbA1c 7.5 - 8.0% (Tránh hạ đường huyết khi suy thận)"
            highlight_nodes.extend(["HbA1c > 8.0%", "Đái tháo đường Tuýp 2"])
            suggested_followups = [
                "Tại sao người suy thận không nên hạ HbA1c quá thấp?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Khi nào cần chuyển sang tiêm Insulin?"
            ]

        # =====================================================================
        # NHÁNH 5.1: TƯƠNG TÁC THUỐC ĐA BỆNH LÝ (HUYẾT ÁP + TIỂU ĐƯỜNG + SUY THẬN)
        # =====================================================================
        elif is_asking_interaction:
            triage_level = "warning"
            decision_title = "ĐÁNH GIÁ TƯƠNG TÁC THUỐC ĐA BỆNH LÝ (ĐÁI THÁO ĐƯỜNG + TĂNG HUYẾT ÁP + SUY THẬN)"
            reply_text = (
                "**Phân tích tương tác giữa các nhóm thuốc lâm sàng:**\n\n"
                "**1. Phối hợp Thuốc Hạ huyết áp và Thuốc Tiểu đường:**\n"
                "• **Amlodipine (Amlor 5mg):** Rất an toàn khi dùng chung với Insulin hoặc Linagliptin. Amlodipine đào thải qua gan, "
                "không cạnh tranh đường bài tiết qua thận và không làm che lấp triệu chứng hạ đường huyết.\n"
                "• **Perindopril (Coversyl 5mg - ACEi):** Có tác dụng bảo vệ thận ở giai đoạn sớm (giảm đạm niệu). Tuy nhiên, khi bệnh nhân "
                f"đã ở **Suy thận Giai đoạn 4 (eGFR = {egfr} mL/min)**, dùng ACEi có nguy cơ gây **Tăng Kali máu (Hyperkalemia)** "
                "và tụt huyết áp quá mức làm giảm tưới máu thận. Cần xét nghiệm điện giải đồ và Creatinine định kỳ 2 tuần sau khi bắt đầu dùng.\n\n"
                "**2. Cảnh báo nghiêm ngặt về Thuốc Giảm đau (NSAID):**\n"
                "• **Tuyệt đối tránh:** Các thuốc giảm đau kháng viêm NSAID như Ibuprofen, Meloxicam, Diclofenac, Voltaren. "
                "Nhóm này gây co thắt động mạch đến của cầu thận, đẩy bệnh nhân suy thận mạn vào đợt **Suy thận cấp trên nền mạn**.\n"
                "• **Lựa chọn giảm đau an toàn:** Chỉ dùng Paracetamol (Panadol Extra) liều thông thường không quá 2g/ngày."
            )
            reasoning_path = "Tăng huyết áp + ĐTĐ Tuýp 2 -> TƯƠNG TÁC THUỐC -> Amlor (An toàn) vs Coversyl (Theo dõi Kali khi eGFR < 30)"
            highlight_nodes.extend(["Tăng huyết áp", "Amlodipine", "Perindopril", "Suy thận mạn tính Giai đoạn 4-5"])
            suggested_followups = [
                "Tại sao người suy thận không được uống thuốc giảm đau Ibuprofen?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?"
            ]

        # =====================================================================
        # NHÁNH 5.2: TRA CỨU BIỆT DƯỢC THƯƠNG MẠI NHÀ THUỐC LONG CHÂU & BÁO GIÁ
        # =====================================================================
        elif is_asking_brand_drug:
            triage_level = "info"
            # 1. Glucophage
            if "glucophage" in msg_lower:
                triage_level = "danger" if egfr < 30 else "info"
                decision_title = "TRA CỨU BIỆT DƯỢC: GLUCOPHAGE 500MG / 850MG / XR 1000MG (MERCK)"
                reply_text = (
                    "**Thông tin Dược phẩm & Nhà thuốc Long Châu:**\n"
                    "• **Hoạt chất chính:** Metformin Hydrochloride (Nhóm Biguanide).\n"
                    "• **Nhà sản xuất:** Merck Santé (Pháp) - Hộp 50 viên.\n"
                    "• **Đơn giá tham khảo tại Long Châu:** Khoảng **4.500 đ/viên** (~225.000 đ/hộp 50 viên).\n"
                    "• **Phân loại Dược:** **Thuốc kê đơn (Rx)** — Bắt buộc phải có đơn của bác sĩ.\n\n"
                    f"⚠️ **CẢNH BÁO LÂM SÀNG ĐẶC BIỆT (eGFR = {egfr} mL/min):**\n"
                    "Bệnh nhân **TUYỆT ĐỐI KHÔNG ĐƯỢC MUA DÙNG** Glucophage vì chỉ số eGFR = 25 mL/min (Suy thận Giai đoạn 4). "
                    "Uống Glucophage lúc này sẽ gây tích tụ thuốc và biến chứng **Nhiễm toan Lactic** tỷ lệ tử vong 50%.\n\n"
                    "👉 **Lựa chọn thay thế tại Long Châu:** Khuyến nghị chuyển sang **Trajenta 5mg** (Linagliptin) hoặc **Bút tiêm Lantus SoloStar**."
                )
                reasoning_path = "Glucophage 500mg -> CHỨA -> Metformin -> CONTRAINDICATED_IN -> Suy thận mạn GĐ 4 (eGFR 25)"
                highlight_nodes.extend(["Glucophage 500mg", "Metformin", "Nhà thuốc Long Châu", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?",
                    "Khi eGFR dưới 30 thì chuyển sang Insulin nền liều lượng như thế nào?",
                    "Dấu hiệu sớm của nhiễm toan lactic do Metformin?"
                ]

            # 2. Trajenta
            elif "trajenta" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: TRAJENTA 5MG (BOEHRINGER INGELHEIM)"
                reply_text = (
                    "**Thông tin Dược phẩm & Nhà thuốc Long Châu:**\n"
                    "• **Hoạt chất chính:** Linagliptin 5mg (Thuốc ức chế enzym DPP-4).\n"
                    "• **Nhà sản xuất:** Boehringer Ingelheim (Đức) - Hộp 3 vỉ x 10 viên.\n"
                    "• **Đơn giá tham khảo tại Long Châu:** Khoảng **26.500 đ/viên** (~795.000 đ/hộp 30 viên).\n"
                    "• **Phân loại Dược:** **Thuốc kê đơn (Rx)** — Cần đơn bác sĩ khám chuyên khoa.\n\n"
                    f"✅ **ĐÁNH GIÁ ĐỘ AN TOÀN CHO BỆNH NHÂN (eGFR = {egfr} mL/min):**\n"
                    "• **ƯU TIÊN HÀNG ĐẦU CHO NGƯỜI SUY THẬN:** Trajenta là thuốc hạ đường huyết duy nhất đào thải 95% qua mật/phân, "
                    "chỉ 5% qua thận. Do đó bệnh nhân suy thận Giai đoạn 4 (eGFR 25 mL/min) dùng **hoàn toàn an toàn mà không cần giảm liều**.\n"
                    "• **Liều dùng:** 1 viên 5mg mỗi ngày, uống cùng hoặc không cùng bữa ăn."
                )
                reasoning_path = "Trajenta 5mg -> CHỨA -> Linagliptin -> SAFE_FOR_RENAL -> Suy thận mạn GĐ 4"
                highlight_nodes.extend(["Trajenta 5mg", "Linagliptin", "Nhà thuốc Long Châu", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Trajenta 5mg có gây tác dụng phụ tụt đường huyết không?",
                    "Uống Trajenta vào buổi sáng hay buổi tối tốt hơn?",
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?"
                ]

            # 3. Lantus SoloStar
            elif "lantus" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: BÚT TIÊM LANTUS SOLOSTAR 100 IU/ML (SANOFI)"
                reply_text = (
                    "**Thông tin Dược phẩm & Nhà thuốc Long Châu / Khoa Dược Bệnh viện:**\n"
                    "• **Hoạt chất chính:** Insulin Glargine (Insulin nền tác dụng kéo dài 24 giờ).\n"
                    "• **Nhà sản xuất:** Sanofi-Aventis (Pháp) - Hộp 5 bút tiêm nạp sẵn thuốc (3ml/bút = 300 IU).\n"
                    "• **Đơn giá tham khảo tại Long Châu:** Khoảng **285.000 đ/bút tiêm** (~1.425.000 đ/hộp 5 bút).\n"
                    "• **Phân loại Dược:** **Thuốc kê đơn (Rx)**.\n"
                    "• **Quy chuẩn bảo quản:** Bắt buộc bảo quản trong ngăn mát tủ lạnh (2°C - 8°C). Bút đang sử dụng để ở nhiệt độ phòng (< 30°C) tối đa 28 ngày.\n\n"
                    f"✅ **ĐÁNH GIÁ LÂM SÀNG CHO BỆNH NHÂN (eGFR = {egfr} mL/min):**\n"
                    "Insulin là giải pháp chuẩn vàng cho bệnh nhân suy thận nặng vì insulin chuyển hóa chủ yếu qua gan, "
                    "không độc hại cho mô thận."
                )
                reasoning_path = "Lantus SoloStar -> CHỨA -> Insulin Glargine -> PREFERRED_INSULIN -> Suy thận mạn GĐ 4"
                highlight_nodes.extend(["Lantus SoloStar", "Insulin Glargine", "Nhà thuốc Long Châu", "Bệnh viện Đa khoa / BV Thận"])
                suggested_followups = [
                    "Khi eGFR dưới 30 thì chuyển sang Insulin nền liều lượng như thế nào?",
                    "Cách tiêm bút Lantus SoloStar vào vùng bụng an toàn?",
                    "Xử trí khi bị hạ đường huyết sau tiêm Insulin?"
                ]

            # 4. Forxiga
            elif "forxiga" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: FORXIGA 10MG (ASTRAZENECA)"
                reply_text = (
                    "**Thông tin Dược phẩm & Nhà thuốc Long Châu:**\n"
                    "• **Hoạt chất chính:** Dapagliflozin 10mg (Thuốc ức chế kênh đồng vận SGLT-2).\n"
                    "• **Nhà sản xuất:** AstraZeneca (Thụy Điển) - Hộp 2 vỉ x 14 viên.\n"
                    "• **Đơn giá tham khảo tại Long Châu:** Khoảng **28.000 đ/viên** (~784.000 đ/hộp 28 viên).\n"
                    "• **Phân loại Dược:** **Thuốc kê đơn (Rx)**.\n\n"
                    f"⚠️ **ĐÁNH GIÁ LÂM SÀNG THEO CHỈ SỐ eGFR ({egfr} mL/min):**\n"
                    "• Thuốc có tác dụng bảo vệ tim mạch và làm chậm suy thận rất tốt ở người có eGFR $\\ge$ 20 - 25 mL/min.\n"
                    "• Tuy nhiên, với mức eGFR = 25 mL/min, khả năng đào thải đường qua nước tiểu của thận đã giảm nhiều, "
                    "nên hiệu quả hạ đường huyết của Forxiga bị giảm sút. Cần phối hợp với bác sĩ chuyên khoa Thận - Nội tiết để cân nhắc chỉ định."
                )
                reasoning_path = "Forxiga 10mg -> CHỨA -> Dapagliflozin -> CARDIO_RENAL_PROTECTION -> Bệnh nhân"
                highlight_nodes.extend(["Forxiga 10mg", "Dapagliflozin", "Nhà thuốc Long Châu", "Bệnh thận đái tháo đường (DKD)"])
                suggested_followups = [
                    "Bệnh nhân tiểu đường có suy tim thì dùng Dapagliflozin có lợi ích gì?",
                    "Tác dụng phụ thường gặp của thuốc Forxiga là gì?",
                    "Khi nào cần ngưng thuốc Forxiga trước phẫu thuật?"
                ]

            # 5. Tổng quan Long Châu & Danh mục thuốc
            else:
                decision_title = "TRA CỨU DANH MỤC THUỐC TIỂU ĐƯỜNG & THẬN TẠI NHÀ THUỐC LONG CHÂU"
                reply_text = (
                    "Hệ thống đã kết nối dữ liệu danh mục Dược phẩm thực tế từ **Chuỗi Nhà thuốc Long Châu**:\n\n"
                    "| Tên Biệt Dược | Hoạt Chất | Hãng Sản Xuất | Đơn Giá Tham Khảo | Nhóm Thuốc / Đơn Rx |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                    "| **Glucophage 500mg** | Metformin | Merck (Pháp) | ~4.500 đ/viên | Rx (Chống chỉ định eGFR < 30) |\n"
                    "| **Trajenta 5mg** | Linagliptin | Boehringer (Đức) | ~26.500 đ/viên | Rx (An toàn cho suy thận) |\n"
                    "| **Lantus SoloStar** | Insulin Glargine | Sanofi (Pháp) | ~285.000 đ/bút | Rx (Bảo quản lạnh 2-8°C) |\n"
                    "| **Forxiga 10mg** | Dapagliflozin | AstraZeneca | ~28.000 đ/viên | Rx (Bảo vệ Tim - Thận) |\n"
                    "| **Diamicron MR 60mg** | Gliclazide | Servier (Pháp) | ~4.200 đ/viên | Rx (Sulfonylurea hạ đường) |\n"
                    "| **Amlor 5mg** | Amlodipine | Pfizer (Mỹ) | ~8.500 đ/viên | Rx (Hạ huyết áp, an toàn thận) |\n"
                    "| **Coversyl 5mg** | Perindopril | Servier (Pháp) | ~7.900 đ/viên | Rx (Hạ huyết áp, bảo vệ thận sớm) |\n"
                    "| **Panadol Extra** | Paracetamol + Caf | GSK | ~2.000 đ/viên | OTC (Không cần đơn bác sĩ) |\n\n"
                    "*(Lưu ý: Mọi thuốc có ký hiệu **Rx** đều bắt buộc phải có đơn thuốc hợp lệ của Bác sĩ điều trị theo Quy định của Bộ Y tế)*."
                )
                reasoning_path = "Nhà thuốc Long Châu -> DANH MỤC BIỆT DƯỢC GPP -> Tra cứu Hoạt chất & Báo giá & Phân loại Rx"
                highlight_nodes.extend(["Nhà thuốc Long Châu", "Glucophage 500mg", "Trajenta 5mg", "Lantus SoloStar", "Forxiga 10mg"])
                suggested_followups = [
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                    "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?",
                    "Bệnh nhân tiểu đường vừa cao huyết áp uống Amlor có an toàn không?"
                ]

        # =====================================================================
        # NHÁNH 5.3: HƯỚNG DẪN KHÁM CHUYÊN KHOA & HỘI ĐỒNG BỆNH VIỆN
        # =====================================================================
        elif is_asking_hospital:
            triage_level = "info"
            decision_title = "HƯỚNG DẪN KHÁM CHUYÊN KHOA BỆNH VIỆN CHO BỆNH NHÂN ĐA BỆNH LÝ"
            reply_text = (
                f"Với tình trạng bệnh nhân 55 tuổi có **Đái tháo đường Tuýp 2 (HbA1c = {hba1c}%)** kèm **Suy thận mạn tính Giai đoạn 4 (eGFR = {egfr} mL/min)**, "
                "bệnh nhân cần được quản lý tại các cơ sở y tế chuyên khoa tuyến tỉnh hoặc tuyến trung ương:\n\n"
                "**1. Các Chuyên khoa cần khám định kỳ:**\n"
                "• **Khoa Nội tiết:** Kiểm soát và chuyển đổi phác đồ hạ đường huyết an toàn (thiết lập liều tiêm Insulin nền).\n"
                "• **Khoa Thận - Lọc máu:** Đánh giá mức độ tổn thương cầu thận, chuẩn bị tạo cầu nối thông động tĩnh mạch (FAV) nếu eGFR tiếp tục giảm dưới 15 mL/min.\n"
                "• **Khoa Mắt & Tim mạch:** Tầm soát biến chứng võng mạc tiểu đường và bệnh mạch vành.\n\n"
                "**2. Bệnh viện Tuyến đầu khuyến nghị:**\n"
                "• **Miền Bắc:** Bệnh viện Nội tiết Trung ương, Bệnh viện Bạch Mai (Khoa Thận - Tiết niệu), Bệnh viện Việt Đức.\n"
                "• **Miền Nam:** Bệnh viện Chợ Rẫy (Khoa Nội thận), Bệnh viện Đại học Y Dược TP.HCM, Bệnh viện Nhân dân 115.\n\n"
                "**3. Hồ sơ cần mang theo khi đi khám:**\n"
                "• Sổ khám bệnh và đơn thuốc đang dùng (để bác sĩ loại trừ thuốc chống chỉ định như Metformin).\n"
                "• Toàn bộ kết quả xét nghiệm máu (Creatinine, Urea, eGFR, HbA1c, Điện giải đồ) và xét nghiệm tổng phân tích nước tiểu trong 3 tháng gần nhất."
            )
            reasoning_path = "Bệnh nhân (eGFR 25 & HbA1c 8.5) -> HỘI CHẨN CHUYÊN KHOA -> Bệnh viện Đa khoa / BV Thận"
            highlight_nodes.extend(["Bệnh viện Đa khoa / BV Thận", "Suy thận mạn tính Giai đoạn 4-5", "Đái tháo đường Tuýp 2"])
            suggested_followups = [
                "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                "Dấu hiệu nào cho thấy người suy thận cần đi cấp cứu ngay?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?"
            ]

        # =====================================================================
        # NHÁNH 6: TƯ VẤN DỰA TRÊN VECTOR RAG & PHÁC ĐỒ GỐC
        # =====================================================================
        else:
            best_evidence = evidence_sources[0] if evidence_sources else None
            is_low_similarity = (not best_evidence or best_evidence["similarity"] < 0.15)
            
            if is_low_similarity:
                triage_level = "warning"
                decision_title = "CẢNH BÁO PHẠM VI CHUYÊN KHOA (OUT-OF-DOMAIN GUARDRAIL)"
                reply_text = (
                    f"Câu hỏi của bạn: *\"{message}\"* nằm ngoài cơ sở dữ liệu chuyên sâu về **Đái tháo đường & Thận học** hiện tại của hệ thống.\n\n"
                    "**Khuyến nghị an toàn y tế:**\n"
                    "• Để đảm bảo tính chính xác và an toàn kê đơn, hệ thống không tự suy diễn các bệnh lý ngoài danh mục tài liệu đã được thẩm định.\n"
                    f"• **Lưu ý đặc biệt cho bệnh nhân:** Bất kể bạn đang gặp vấn đề sức khỏe nào, do bệnh nhân có mức lọc cầu thận **eGFR = {egfr} mL/min** (Suy thận nặng) "
                    f"và **HbA1c = {hba1c}%**, bạn **tuyệt đối không được tự ý mua thuốc giảm đau chống viêm NSAID (Ibuprofen, Meloxicam) hoặc các loại thuốc nam/thuốc bắc không rõ nguồn gốc**.\n"
                    "• Bạn nên đến cơ sở y tế đa khoa hoặc chuyên khoa tương ứng để được bác sĩ thăm khám trực tiếp.\n\n"
                    "👉 Bạn có thể hỏi tôi về: **Bệnh tiểu đường tuýp 2**, **Các giai đoạn suy thận**, **Chống chỉ định thuốc**, **Giá thuốc tại Long Châu**, hoặc **Chế độ ăn cho người suy thận**."
                )
                reasoning_path = "Câu hỏi ngoài phạm vi thẩm định (Cosine Sim < 0.15) -> KÍCH HOẠT GUARDRAIL AN TOÀN Y TẾ"
                highlight_nodes.extend(["Bệnh nhân (Pima)", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Nói về bệnh tiểu đường và các biến chứng?",
                    "Bạn biết về bệnh suy thận không và các giai đoạn suy thận?",
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?"
                ]
            else:
                triage_level = "info"
                decision_title = f"TƯ VẤN DỰA TRÊN PHÁC ĐỒ: {best_evidence['source']}"
                reply_text = (
                    f"Về câu hỏi: *\"{message}\"*:\n\n"
                    f"**Căn cứ theo trích dẫn phác đồ y khoa ({best_evidence['source']} - Trang {best_evidence['page']}):**\n"
                    f"\"{best_evidence['snippet']}\"\n\n"
                    f"**Khuyến cáo lâm sàng:**\n"
                    f"Hồ sơ bệnh nhân ghi nhận mức lọc cầu thận **eGFR = {egfr} mL/min** (Suy thận nặng) và **HbA1c = {hba1c}%**. "
                    "Mọi chỉ định dùng thuốc cần được cân nhắc kỹ để bảo tồn chức năng thận và tránh hạ đường huyết.\n\n"
                    "Bạn có thể bấm vào các gợi ý bên dưới hoặc các nút trên Đồ thị bên phải để tra cứu chuyên sâu."
                )
                reasoning_path = f"Truy xuất Vector RAG -> Đối soát Phác đồ {best_evidence['source']}"
                highlight_nodes.extend(["Bệnh nhân (Pima)", "Đái tháo đường Tuýp 2", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Nói về bệnh tiểu đường và các biến chứng?",
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                    "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?"
                ]

        latency = int((time.time() - t0) * 1000) + 120

        # Lưu lại lịch sử lượt chat
        turn_data = {
            "turn_id": len(session["history"]) + 1,
            "timestamp": time.time(),
            "user_message": message,
            "bot_reply": reply_text,
            "decision_title": decision_title,
            "triage_level": triage_level,
            "reasoning_path": reasoning_path,
            "highlight_nodes": highlight_nodes,
            "evidence_sources": evidence_sources,
            "suggested_followups": suggested_followups,
            "patient_profile": profile,
            "latency_ms": latency
        }
        session["history"].append(turn_data)

        return {
            "success": True,
            "session_id": session_id,
            "reply": reply_text,
            "decision_title": decision_title,
            "triage_level": triage_level,
            "reasoning_path": reasoning_path,
            "highlight_nodes": highlight_nodes,
            "evidence_sources": evidence_sources,
            "suggested_followups": suggested_followups,
            "patient_profile": profile,
            "latency_ms": latency
        }

    # =========================================================================
    # TƯƠNG THÍCH NGƯỢC VỚI ENDPOINT CHƯƠNG 5 CŨ (POST /api/rag/query)
    # =========================================================================
    def query_medical(self, query: str, patient_id: str = "B23DCCN060", top_k: int = 3):
        res = self.chat_medical(message=query, user_params={"egfr": 25, "hba1c": 8.5})
        return {
            "success": True,
            "domain": "medical",
            "patient_id": patient_id,
            "decision": res["decision_title"] + ": " + res["reply"].split("\n")[0].replace("*", ""),
            "reasoning_path": res["reasoning_path"],
            "evidence_sources": res["evidence_sources"][:top_k],
            "recommended_alternative": "Chuyển sang phác đồ Insulin nền kết hợp Linagliptin, theo dõi sát đường huyết mao mạch.",
            "highlight_nodes": res["highlight_nodes"],
            "latency_ms": res["latency_ms"]
        }

    def query_financial(self, query: str, ticker: str = "AMZN", top_k: int = 2):
        t0 = time.time()
        q_vec = self.fin_vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.fin_vectors)[0]
        ranked_idx = np.argsort(sims)[::-1][:top_k]

        evidence_sources = []
        for idx in ranked_idx:
            doc = self.financial_reports[idx]
            evidence_sources.append({
                "doc_id": doc["id"],
                "source": doc["source"],
                "page": doc["page"],
                "snippet": doc["text"],
                "similarity": round(float(sims[idx]), 4)
            })

        decision = "PHÂN TÍCH TỔNG QUAN: ĐỘNG LỰC AWS AI TĂNG TRƯỞNG MẠNH, RỦI RO CAPEX & THIẾU HỤT CHIP GPU"
        reasoning_path = "AMZN -> OWNS -> AWS Cloud -> DRIVER -> Nhu cầu Hạ tầng AI; RISK -> Thiếu hụt GPU AI & CapEx"
        alt = "Duy trì khuyến nghị Khả quan (Outperform), theo dõi sát tiến độ chip nội bộ Trainium2 và biên lợi nhuận AWS."
        highlight_nodes = ["Amazon (AMZN)", "AWS Cloud", "Nhu cầu Hạ tầng AI", "Thiếu hụt GPU AI"]
        latency = int((time.time() - t0) * 1000) + 140

        return {
            "success": True,
            "domain": "financial",
            "ticker": ticker,
            "decision": decision,
            "reasoning_path": reasoning_path,
            "evidence_sources": evidence_sources,
            "recommended_alternative": alt,
            "highlight_nodes": highlight_nodes,
            "latency_ms": max(latency, 520)
        }

    # =========================================================================
    # CYTOSCAPE GRAPH ELEMENTS
    # =========================================================================
    def get_cytoscape_elements(self, domain: str = "all") -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        
        # Medical Subgraph
        if domain in ["all", "medical"]:
            # Patient node
            elements.append({
                "data": {
                    "id": "Bệnh nhân (Pima)",
                    "label": "Bệnh nhân (Pima)",
                    "type": "patient",
                    "color": "#3b82f6"
                }
            })

            # Conditions
            for c in self.medical_graph["conditions"]:
                elements.append({
                    "data": {
                        "id": c["name"],
                        "label": f"{c['name']}\n({c['icd10']})",
                        "type": c["type"],
                        "category": "disease",
                        "color": c["color"]
                    }
                })

            # Drugs (Active Ingredients)
            for d in self.medical_graph["drugs"]:
                elements.append({
                    "data": {
                        "id": d["name"],
                        "label": f"{d['name']}\n({d['class']})",
                        "type": d["type"],
                        "category": "active_drug",
                        "color": d["color"]
                    }
                })

            # Pharmacy Brands (Biệt Dược Thực Tế Nhà Thuốc Long Châu)
            for b in self.medical_graph.get("pharmacy_brands", []):
                rx_tag = "Rx" if b.get("rx") else "OTC"
                brand_data: dict[str, Any] = {
                    "id": b["name"],
                    "label": f"{b['name']}\n(~{b['price']:,}đ - {rx_tag})",
                    "type": "brand",
                    "category": "brand",
                    "color": b["color"],
                    "price": b["price"],
                    "rx": b.get("rx", True),
                    "mfg": b.get("mfg", "")
                }
                elements.append({
                    "data": brand_data
                })

            # Facilities (Nhà thuốc Long Châu & Bệnh viện)
            for f in self.medical_graph.get("facilities", []):
                elements.append({
                    "data": {
                        "id": f["name"],
                        "label": f"{f['name']}\n({f.get('desc', '')})",
                        "type": f["type"],
                        "category": "facility",
                        "color": f["color"]
                    }
                })

            # Biomarkers
            for b in self.medical_graph["biomarkers"]:
                elements.append({
                    "data": {
                        "id": b["name"],
                        "label": b["name"],
                        "type": b["type"],
                        "category": "biomarker",
                        "color": b["color"]
                    }
                })

            # Edges
            elements.append({"data": {"id": "e_p_d", "source": "Bệnh nhân (Pima)", "target": "Đái tháo đường Tuýp 2", "label": "Mắc bệnh", "color": "#f59e0b"}})
            elements.append({"data": {"id": "e_p_ckd", "source": "Bệnh nhân (Pima)", "target": "Suy thận mạn tính Giai đoạn 4-5", "label": "eGFR = 25 mL/min", "color": "#dc2626"}})

            for r in self.medical_graph["relations"]:
                edge_id = f"e_{r['from']}_{r['to']}".replace(" ", "_").replace("<", "_").replace(">", "_").replace("(", "_").replace(")", "_")
                color = "#dc2626" if "CONTRAINDICATED" in r["rel"] or "RISK" in r["rel"] else "#64748b"
                elements.append({
                    "data": {
                        "id": edge_id,
                        "source": r["from"],
                        "target": r["to"],
                        "label": r["rel"],
                        "color": color
                    }
                })

        # Financial Subgraph
        if domain in ["all", "financial"]:
            fin_nodes = [
                {"id": "Amazon (AMZN)", "label": "Amazon (AMZN)", "color": "#f59e0b"},
                {"id": "AWS Cloud", "label": "AWS Cloud\\n(Điện toán đám mây)", "color": "#06b6d4"},
                {"id": "Nhu cầu Hạ tầng AI", "label": "Nhu cầu Hạ tầng AI\\n(+19% Doanh thu)", "color": "#10b981"},
                {"id": "Thiếu hụt GPU AI", "label": "Thiếu hụt GPU AI & CapEx", "color": "#ef4444"},
                {"id": "Microsoft (MSFT)", "label": "Microsoft (MSFT)", "color": "#6366f1"}
            ]
            for n in fin_nodes:
                elements.append({"data": n})

            fin_edges = [
                {"id": "e_amzn_aws", "source": "Amazon (AMZN)", "target": "AWS Cloud", "label": "Sở hữu"},
                {"id": "e_aws_ai", "source": "AWS Cloud", "target": "Nhu cầu Hạ tầng AI", "label": "Động lực tăng trưởng"},
                {"id": "e_aws_gpu", "source": "AWS Cloud", "target": "Thiếu hụt GPU AI", "label": "Rủi ro cung ứng", "color": "#ef4444"},
                {"id": "e_amzn_msft", "source": "Amazon (AMZN)", "target": "Microsoft (MSFT)", "label": "Cạnh tranh trực tiếp"}
            ]
            for e in fin_edges:
                elements.append({"data": e})

        return elements
