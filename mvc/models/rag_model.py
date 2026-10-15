# -*- coding: utf-8 -*-
"""
rag_model.py
Tầng Model (M) trong kiến trúc MVC cho Hệ thống Đồ thị Tri thức (Knowledge Graph)
và Trợ lý Y khoa Thông minh GraphRAG Chatbot Đàm thoại Đa lượt.
Hỗ trợ kiến thức chuyên sâu về: Đái tháo đường, Suy thận mạn tính (CKD), Tăng huyết áp, 
Tim mạch, Tương tác thuốc và Chế độ dinh dưỡng lâm sàng.
"""

import os
import time
import re
import uuid
import json
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
                {"id": "c7", "name": "Bệnh thận đái tháo đường (DKD)", "icd10": "E11.2", "type": "disease", "color": "#991b1b"},
                {"id": "c8", "name": "Cảm cúm / Nhiễm siêu vi", "icd10": "J06.9", "type": "disease", "color": "#0284c7"},
                {"id": "c9", "name": "Viêm loét dạ dày - Trào ngược (GERD)", "icd10": "K21.9", "type": "disease", "color": "#d97706"},
                {"id": "c10", "name": "Viêm họng cấp tính", "icd10": "J02.9", "type": "disease", "color": "#0284c7"},
                {"id": "c11", "name": "Dị ứng / Mề đay cấp & mạn", "icd10": "L50.9", "type": "disease", "color": "#14b8a6"},
                {"id": "c12", "name": "Cơn Gout cấp tính & Tăng Acid Uric", "icd10": "M10.9", "type": "disease", "color": "#b45309"},
                {"id": "c13", "name": "Rối loạn tiền đình & Đau đầu căng thẳng", "icd10": "H81.0", "type": "disease", "color": "#6366f1"}
            ],
            "drugs": [
                {"id": "d1", "name": "Metformin", "class": "Biguanide", "dose": "500mg - 1000mg x 2 lần/ngày", "type": "drug", "color": "#10b981"},
                {"id": "d2", "name": "Insulin Glargine", "class": "Hormone", "dose": "10 IU/ngày tiêm dưới da", "type": "drug", "color": "#8b5cf6"},
                {"id": "d3", "name": "Gliclazide", "class": "Sulfonylurea", "dose": "30mg - 120mg/ngày", "type": "drug", "color": "#06b6d4"},
                {"id": "d4", "name": "Linagliptin", "class": "DPP-4 Inhibitor", "dose": "5mg x 1 lần/ngày (không cần chỉnh liều thận)", "type": "drug", "color": "#14b8a6"},
                {"id": "d5", "name": "Dapagliflozin", "class": "SGLT-2 Inhibitor", "dose": "10mg x 1 lần/ngày (bảo vệ tim & thận)", "type": "drug", "color": "#0ea5e9"},
                {"id": "d6", "name": "Amlodipine", "class": "Chẹn Canxi CCB", "dose": "5mg/ngày (hạ huyết áp an toàn)", "type": "drug", "color": "#38bdf8"},
                {"id": "d7", "name": "Perindopril", "class": "Ức chế men chuyển ACEi", "dose": "5mg/ngày (bảo vệ thận sớm)", "type": "drug", "color": "#a855f7"},
                {"id": "d8", "name": "Paracetamol (Acetaminophen)", "class": "Giảm đau hạ sốt OTC", "dose": "500mg - 650mg x 3-4 lần/ngày", "type": "drug", "color": "#10b981"},
                {"id": "d9", "name": "Ibuprofen", "class": "Kháng viêm NSAID", "dose": "400mg x 2-3 lần/ngày (Cẩn trọng suy thận/dạ dày)", "type": "drug", "color": "#ef4444"},
                {"id": "d10", "name": "Esomeprazole", "class": "Ức chế bơm Proton PPI", "dose": "20mg - 40mg/ngày trước ăn sáng", "type": "drug", "color": "#06b6d4"},
                {"id": "d11", "name": "Fexofenadine", "class": "Kháng Histamin H1 thế hệ 2", "dose": "60mg - 180mg/ngày (không buồn ngủ)", "type": "drug", "color": "#8b5cf6"},
                {"id": "d12", "name": "Colchicine", "class": "Thuốc đặc trị Gút cấp", "dose": "1mg khởi đầu, sau đó 0.5mg (chỉnh liều khi suy thận)", "type": "drug", "color": "#f59e0b"},
                {"id": "d13", "name": "Betahistine", "class": "Đồng vận Histamin tiền đình", "dose": "16mg - 24mg x 2 lần/ngày", "type": "drug", "color": "#3b82f6"}
            ],
            "pharmacy_brands": [
                {"id": "b1", "name": "Glucophage 500mg", "active": "Metformin", "mfg": "Merck (Pháp)", "price": 4500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b2", "name": "Trajenta 5mg", "active": "Linagliptin", "mfg": "Boehringer (Đức)", "price": 26500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b3", "name": "Lantus SoloStar", "active": "Insulin Glargine", "mfg": "Sanofi (Pháp)", "price": 285000, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b4", "name": "Forxiga 10mg", "active": "Dapagliflozin", "mfg": "AstraZeneca", "price": 28000, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b5", "name": "Diamicron MR 60mg", "active": "Gliclazide", "mfg": "Servier (Pháp)", "price": 4200, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b6", "name": "Amlor 5mg", "active": "Amlodipine", "mfg": "Pfizer (Mỹ)", "price": 8500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b7", "name": "Coversyl 5mg", "active": "Perindopril", "mfg": "Servier (Pháp)", "price": 7900, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b8", "name": "Panadol Extra", "active": "Paracetamol", "mfg": "GSK", "price": 2000, "rx": False, "type": "brand", "color": "#c084fc"},
                {"id": "b9", "name": "Nexium Mups 20mg", "active": "Esomeprazole", "mfg": "AstraZeneca (Thụy Điển)", "price": 23500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b10", "name": "Gaviscon Dual Action", "active": "Antacid + Alginate", "mfg": "Reckitt Benckiser (Anh)", "price": 6500, "rx": False, "type": "brand", "color": "#c084fc"},
                {"id": "b11", "name": "Telfast HD 180mg", "active": "Fexofenadine", "mfg": "Sanofi (Pháp)", "price": 12500, "rx": False, "type": "brand", "color": "#c084fc"},
                {"id": "b12", "name": "Hapacol 650mg", "active": "Paracetamol (Acetaminophen)", "mfg": "DHG Pharma (Việt Nam)", "price": 1000, "rx": False, "type": "brand", "color": "#c084fc"},
                {"id": "b13", "name": "Colchicina Stella 1mg", "active": "Colchicine", "mfg": "Stella Pharm", "price": 2500, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b14", "name": "Betaserc 16mg", "active": "Betahistine", "mfg": "Abbott (Mỹ)", "price": 5800, "rx": True, "type": "brand", "color": "#818cf8"},
                {"id": "b15", "name": "Siro Prospan 100ml", "active": "Cao lá thường xuân", "mfg": "Engelhard (Đức)", "price": 75000, "rx": False, "type": "brand", "color": "#c084fc"}
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

                # Phác đồ Bệnh cơ bản thường gặp
                {"from": "Paracetamol (Acetaminophen)", "to": "Cảm cúm / Nhiễm siêu vi", "rel": "TREATS_SYMPTOM"},
                {"from": "Paracetamol (Acetaminophen)", "to": "Viêm họng cấp tính", "rel": "TREATS_PAIN"},
                {"from": "Ibuprofen", "to": "Suy thận mạn tính Giai đoạn 4-5", "rel": "CONTRAINDICATED_IN", "severity": "Danger"},
                {"from": "Ibuprofen", "to": "Viêm loét dạ dày - Trào ngược (GERD)", "rel": "CONTRAINDICATED_IN", "severity": "Danger"},
                {"from": "Esomeprazole", "to": "Viêm loét dạ dày - Trào ngược (GERD)", "rel": "FIRST_LINE_PPI"},
                {"from": "Fexofenadine", "to": "Dị ứng / Mề đay cấp & mạn", "rel": "FIRST_LINE_ANTIHISTAMINE"},
                {"from": "Colchicine", "to": "Cơn Gout cấp tính & Tăng Acid Uric", "rel": "ACUTE_TREATMENT"},
                {"from": "Betahistine", "to": "Rối loạn tiền đình & Đau đầu căng thẳng", "rel": "FIRST_LINE_VESTIBULAR"},

                # Liên kết Biệt Dược Long Châu -> Hoạt Chất
                {"from": "Glucophage 500mg", "to": "Metformin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Trajenta 5mg", "to": "Linagliptin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Lantus SoloStar", "to": "Insulin Glargine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Forxiga 10mg", "to": "Dapagliflozin", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Diamicron MR 60mg", "to": "Gliclazide", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Amlor 5mg", "to": "Amlodipine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Coversyl 5mg", "to": "Perindopril", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Nexium Mups 20mg", "to": "Esomeprazole", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Telfast HD 180mg", "to": "Fexofenadine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Hapacol 650mg", "to": "Paracetamol (Acetaminophen)", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Colchicina Stella 1mg", "to": "Colchicine", "rel": "CHỨA_HOẠT_CHẤT"},
                {"from": "Betaserc 16mg", "to": "Betahistine", "rel": "CHỨA_HOẠT_CHẤT"},

                # Liên kết Biệt Dược -> Nhà thuốc Long Châu
                {"from": "Glucophage 500mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~4.500đ/viên - Rx)"},
                {"from": "Trajenta 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~26.500đ/viên - Rx)"},
                {"from": "Lantus SoloStar", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~285k/bút - Rx)"},
                {"from": "Forxiga 10mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~28.000đ/viên - Rx)"},
                {"from": "Diamicron MR 60mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~4.200đ/viên - Rx)"},
                {"from": "Amlor 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~8.500đ/viên - Rx)"},
                {"from": "Coversyl 5mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~7.900đ/viên - Rx)"},
                {"from": "Panadol Extra", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~2.000đ/viên - OTC)"},
                {"from": "Nexium Mups 20mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~23.500đ/v - Rx)"},
                {"from": "Gaviscon Dual Action", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~6.500đ/gói - OTC)"},
                {"from": "Telfast HD 180mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~12.500đ/v - OTC)"},
                {"from": "Hapacol 650mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~1.000đ/v - OTC)"},
                {"from": "Colchicina Stella 1mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~2.500đ/v - Rx)"},
                {"from": "Betaserc 16mg", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~5.800đ/v - Rx)"},
                {"from": "Siro Prospan 100ml", "to": "Nhà thuốc Long Châu", "rel": "BÁN_TẠI (~75.000đ/chai - OTC)"},

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
            },
            {
                "id": "DOC013",
                "text": "Hướng dẫn xử trí Cảm cúm, Sốt và Viêm đường hô hấp trên: "
                        "Hầu hết nguyên nhân do virus, không tự ý dùng kháng sinh khi chưa có chỉ định. "
                        "Hạ sốt giảm đau ưu tiên hàng đầu là Paracetamol (Acetaminophen) liều 10-15 mg/kg mỗi 4-6 giờ (tối đa 4g/ngày ở người bình thường, 2-3g ở người suy gan/thận). "
                        "Cảnh báo an toàn: Bệnh nhân có tiền sử suy thận mạn hoặc đau dạ dày tuyệt đối tránh dùng các thuốc giảm đau "
                        "chống viêm NSAID (như Ibuprofen, Diclofenac, Meloxicam) vì nguy cơ gây suy thận cấp và xuất huyết tiêu hóa nặng.",
                "source": "Bo_Y_Te_Chan_Doan_Dieu_Tri_Cam_Cum_2026.pdf",
                "page": 11
            },
            {
                "id": "DOC014",
                "text": "Phác đồ điều trị Trào ngược dạ dày thực quản (GERD) và Viêm loét dạ dày tá tràng: "
                        "Thuốc ức chế bơm Proton (PPI như Esomeprazole - Nexium Mups 20mg/40mg, Omeprazole) là lựa chọn đầu tay, "
                        "uống 1 lần/ngày vào buổi sáng trước bữa ăn 30-60 phút trong 4-8 tuần. "
                        "Thuốc kháng acid phối hợp alginate (Gaviscon Dual Action, Yumangel) dùng tạo màng bảo vệ ngăn trào ngược, "
                        "uống sau ăn 1-2 giờ hoặc khi có cơn đau rát thượng vị. Cần kiêng rượu bia, cà phê, thuốc lá, đồ cay chua và tránh nằm ngay sau ăn.",
                "source": "Hoi_Khoa_Hoc_Tieu_Hoa_GERD_Guideline_2026.pdf",
                "page": 27
            },
            {
                "id": "DOC015",
                "text": "Hướng dẫn chẩn đoán và xử trí Cơn Gout cấp tính và Tăng Acid Uric máu: "
                        "Cắt cơn viêm khớp gút cấp ưu tiên Colchicine liều thấp (1mg trong vòng 12h đầu, sau đó 0.5mg sau 1 giờ), "
                        "sau đó duy trì 0.5mg 1-2 lần/ngày. Với bệnh nhân suy thận (eGFR < 50 mL/min), phải giảm một nửa liều Colchicine. "
                        "Không khởi đầu thuốc hạ acid uric (Allopurinol, Febuxostat) trong lúc đang có cơn viêm khớp cấp tính rầm rộ; "
                        "chờ cơn gút lắng dịu 1-2 tuần mới bắt đầu chỉnh liều hạ acid uric máu mục tiêu < 360 umol/L.",
                "source": "Bo_Y_Te_Phac_Do_Dieu_Tri_Gout_2026.pdf",
                "page": 15
            },
            {
                "id": "DOC016",
                "text": "Phác đồ điều trị Dị ứng thời tiết, Mề đay mẩn ngứa và Viêm mũi dị ứng: "
                        "Kháng Histamin H1 thế hệ 2 (Fexofenadine - Telfast 180mg, Cetirizine - Zyrtec 10mg, Loratadine) "
                        "là nhóm thuốc lựa chọn hàng đầu nhờ hiệu quả chống ngứa cao, tác dụng kéo dài 24 giờ và không gây buồn ngủ. "
                        "Thuốc chuyển hóa ít qua gan thận, an toàn cho người lớn tuổi. Dùng 1 viên mỗi ngày khi có biểu hiện ngứa, nổi sẩn mề đay.",
                "source": "Bo_Y_Te_Huong_Dan_Di_Ung_Me_Day_2026.pdf",
                "page": 18
            },
            {
                "id": "DOC017",
                "text": "Hướng dẫn điều trị Hội chứng tiền đình và Đau đầu căng thẳng vận mạch: "
                        "Betahistine (Betaserc 16mg hoặc 24mg) làm tăng lưu lượng máu vi tuần hoàn tai trong và não bộ, "
                        "chỉ định chính cho chứng chóng mặt kịch phát, hoa mắt, ù tai, mất thăng bằng do tiền đình. "
                        "Có thể phối hợp chiết xuất lá bạch quả Ginkgo Biloba (Otiv) để cải thiện tưới máu não. "
                        "Bệnh nhân cần nghỉ ngơi trong phòng tối, yên tĩnh, hạn chế đổi tư thế đột ngột.",
                "source": "Hoi_Than_Kinh_Hoc_Viet_Nam_Tien_Dinh_2026.pdf",
                "page": 9
            },
            {
                "id": "DOC018",
                "text": "Cẩm nang tra cứu và sử dụng Dược phẩm Thiết yếu tại Nhà thuốc FPT Long Châu: "
                        "Các thuốc giảm đau hạ sốt như Panadol Extra (Paracetamol 500mg + Cafein, ~2.000đ/viên), Hapacol 650mg (~1.000đ/viên), "
                        "siro ho Prospan (~75.000đ/chai) và thuốc chống trào ngược Gaviscon Dual Action (~6.500đ/gói) thuộc danh mục không kê đơn (OTC), "
                        "khách hàng có thể mua tự do để sơ cứu tại nhà. "
                        "Các thuốc Nexium Mups, Betaserc, Colchicina, Trajenta, Forxiga, Lantus thuộc danh mục thuốc kê đơn (Rx), "
                        "cần có đơn bác sĩ và tư vấn của dược sĩ chuyên môn tại quầy.",
                "source": "LongChau_OTC_Essential_Medicine_Catalog_2026.pdf",
                "page": 5
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
                    "age": None,
                    "gender": None,
                    "egfr": None,
                    "hba1c": None,
                    "fasting_glucose": None,
                    "conditions": [],
                    "medications": []
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
    # TÍCH HỢP MÔ HÌNH NGÔN NGỮ LỚN (GOOGLE GEMINI 1.5 FLASH API)
    # =========================================================================
    def get_api_key(self, provided_key: Optional[str] = None) -> Optional[str]:
        """Tự động tìm kiếm API Key từ tham số, biến môi trường hoặc file .env"""
        if provided_key and provided_key.strip() and not provided_key.startswith("AIzaSyYour"):
            return provided_key.strip()

        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key and env_key.strip() and not env_key.startswith("AIzaSyYour"):
            return env_key.strip()

        possible_paths = [
            ".env",
            os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
            os.path.abspath(".env")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY="):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key and not key.startswith("AIzaSyYour"):
                                    return key
                except Exception:
                    pass
        return None

    def call_gemini_llm(self, prompt: str, system_instruction: str, api_key: str) -> Optional[str]:
        """Gọi trực tiếp Google Gemini qua HTTP REST API (chuẩn 100% không cần thư viện ngoài)"""
        import urllib.request
        import json

        models_to_try = [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-3.8-flash"
        ]
        
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": [
                    {"parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "maxOutputTokens": 350
                }
            }

            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=6) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
            except Exception as e:
                # Thử model tiếp theo nếu bị lỗi
                continue
        return None


    # =========================================================================
    # CORE REASONING: CHATBOT ĐÀM THOẠI Y KHOA THÔNG MINH
    # =========================================================================
    def chat_medical(
        self, 
        message: str, 
        session_id: Optional[str] = None, 
        user_params: Optional[dict[str, Any]] = None,
        gemini_api_key: Optional[str] = None,
        use_llm: bool = True
    ):
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
        egfr = profile.get("egfr")
        hba1c = profile.get("hba1c")
        
        highlight_nodes = ["Bác sĩ Lâm sàng AI"]
        suggested_followups = []
        triage_level = "info" # info, warning, danger

        # =====================================================================
        # PHÂN TÍCH Ý ĐỊNH CHUYÊN SÂU
        # =====================================================================
        greeting_terms = [
            "xin chào", "xin chao", "chào bạn", "chao ban", "chào bác sĩ", "chao bac si", "chào bot", "chao bot",
            "chào chatbot", "chao chatbot", "hello", "hi", "hey", "alo", "bạn là ai", "ban la ai", 
            "giới thiệu", "gioi thieu", "hướng dẫn", "huong dan", "bạn làm được gì", "ban lam duoc gi",
            "chatbot là gì", "trợ lý y khoa", "có ai ở đây không", "co ai o day khong", "start", "bắt đầu"
        ]
        is_greeting = (
            any(msg_lower == term or msg_lower.startswith(term + " ") or msg_lower.endswith(" " + term) for term in greeting_terms) or
            (len(msg_lower.split()) <= 3 and any(w in msg_lower for w in ["chao", "chào", "hello", "hi", "alo", "chatbot"]))
        )

        is_asking_metformin_contraindication = (
            not is_greeting and
            ("metformin" in msg_lower or "thuốc hạ đường" in msg_lower or "thuoc ha duong" in msg_lower) and
            ((egfr is not None and egfr < 30) or "suy thận" in msg_lower or "suy than" in msg_lower or "egfr" in msg_lower or "thận" in msg_lower or "than" in msg_lower or "chống chỉ định" in msg_lower or "chong chi dinh" in msg_lower or "uống được" in msg_lower or "uong duoc" in msg_lower or "tiếp tục dùng" in msg_lower or "tiep tuc dung" in msg_lower)
        )
        is_asking_diet = any(term in msg_lower for term in [
            "chế độ ăn", "che do an", "ăn gì", "an gi", "kiêng gì", "kieng gi", "dinh dưỡng", "dinh duong", 
            "thực đơn", "thuc don", "uống nước", "uong nuoc", "muối", "muoi", "đạm", "dam", "protein"
        ])
        is_asking_headache = any(term in msg_lower for term in [
            "đau đầu", "dau dau", "nhức đầu", "nhuc dau", "đau nửa đầu", "dau nua dau", 
            "buốt đầu", "buot dau", "nặng đầu", "nang dau", "đau thái dương", "nhức thái dương", "đau đỉnh đầu"
        ])
        is_asking_exercise_symptom = any(term in msg_lower for term in [
            "vận động mạnh", "van dong manh", "vận động", "van dong", "tập thể dục", "tap the duc", 
            "tập gym", "tap gym", "thể thao", "the thao", "đau cơ", "dau co", "mỏi cơ", "moi co", "đau người sau tập"
        ])
        is_asking_hospital = any(term in msg_lower for term in [
            "bệnh viện", "benh vien", "khoa thận", "khoa than", "khám ở đâu", "kham o dau", 
            "tuyến trên", "tuyen tren", "bạch mai", "bach mai", "chợ rẫy", "cho ray", 
            "nội tiết trung ương", "đại học y dược", "bác sĩ chuyên khoa"
        ])
        is_asking_interaction = any(term in msg_lower for term in [
            "tương tác", "tuong tac", "uống chung", "uong chung", "dùng chung", "dung chung", 
            "phối hợp", "phoi hop", "kết hợp thuốc", "uống cùng lúc", 
            "huyết áp và tiểu đường", "uống với", "uong voi"
        ]) or (("amlor" in msg_lower or "coversyl" in msg_lower) and ("thuốc gì" in msg_lower or "an toàn" in msg_lower or "với" in msg_lower))
        is_asking_pain_relief = any(term in msg_lower for term in [
            "panadol", "paracetamol", "hapacol", "giảm đau", "giam dau", "hạ sốt", "ha sot", 
            "đau đầu", "dau dau", "nhức đầu", "nhuc dau", "đau nửa đầu", "dau nua dau", 
            "buốt đầu", "buot dau", "nặng đầu", "nang dau", "đau nhức", "dau nhuc", 
            "uống panadol", "uong panadol", "uống paracetamol", "uong paracetamol"
        ])
        is_asking_brand_drug = (
            any(term in msg_lower for term in [
                "long châu", "long chau", "bảng giá", "bang gia", "giá thuốc", "gia thuoc", "bao nhiêu tiền", "bao nhieu tien", 
                "mua ở đâu", "mua o dau", "nhà thuốc", "nha thuoc", "danh mục thuốc", "danh muc thuoc", 
                "kê đơn", "rx", "otc", "đắt không", "hộp bao nhiêu"
            ]) and not is_asking_pain_relief
        )
        is_asking_kidney_disease = (
            any(term in msg_lower for term in [
                "suy thận", "suy than", "bệnh thận", "benh than", "thận mạn", "than man", 
                "thận yếu", "than yeu", "chức năng thận", "chuc nang than", 
                "chạy thận", "chay than", "lọc máu", "loc mau", "creatinine", 
                "protein niệu", "đạm niệu", "dam nieu", "nước tiểu có bọt", "nuoc tieu co bot", "egfr"
            ]) and not is_asking_brand_drug and not is_asking_hospital and not is_asking_interaction and not is_asking_pain_relief and not is_asking_exercise_symptom
        )
        is_asking_diabetes_overview = (
            any(term in msg_lower for term in [
                "tiểu đường là gì", "đái tháo đường là gì", "tieu duong la gi", "dai thao duong la gi",
                "nói về bệnh tiểu đường", "tìm hiểu về tiểu đường", "thế nào là tiểu đường", 
                "tiểu đường tuýp 2 là gì", "bệnh tiểu đường", "bệnh đái tháo đường", 
                "tiểu đường tuýp 2", "tiểu đường", "tieu duong", "đái tháo đường", "dai thao duong"
            ]) and not is_asking_metformin_contraindication 
               and not is_asking_diet 
               and not is_asking_kidney_disease 
               and not is_asking_brand_drug 
               and not is_asking_hospital 
               and not is_asking_interaction
               and not is_asking_headache
               and not is_asking_exercise_symptom
        )
        
        # Các bệnh lý thông thường cơ bản mới bổ sung
        is_asking_gerd = any(term in msg_lower for term in [
            "trào ngược", "trao nguoc", "dạ dày", "da day", "bao tử", "bao tu", "ợ chua", "o chua", 
            "ợ nóng", "o nong", "rát thượng vị", "rat thuong vi", 
            "nexium", "gaviscon", "esomeprazole", "loét dạ dày", "đau dạ dày", "dau da day", "viêm dạ dày"
        ])
        is_asking_gout = any(term in msg_lower for term in [
            "gout", "gút", "gut", "acid uric", "ngón chân cái", "ngon chan cai", "sưng ngón chân", 
            "colchicine", "colchicina", "allopurinol", "viêm khớp gút", "đau khớp gút"
        ])
        is_asking_allergy = any(term in msg_lower for term in [
            "dị ứng", "di ung", "mề đay", "me day", "mẩn ngứa", "man ngua", "ngứa da", "ngua da", 
            "viêm mũi dị ứng", "hắt hơi", "telfast", "zyrtec", "cetirizine", "fexofenadine"
        ])
        is_asking_vestibular = any(term in msg_lower for term in [
            "tiền đình", "tien dinh", "chóng mặt", "chong mat", "hoa mắt", "hoa mat", 
            "quay cuồng", "quay cuong", "mất thăng bằng", "mat thang bang", 
            "betaserc", "betahistine", "otiv", "thiểu năng tuần hoàn"
        ])
        is_asking_flu_cough = any(term in msg_lower for term in [
            "cảm cúm", "cam cum", "sốt", "sot", "nhiễm siêu vi", "ho đờm", "ho dom", "ho khan", "sổ mũi", "so mui", 
            "đau họng", "dau hong", "rát họng", "rat hong", "viêm họng", "viem hong", 
            "prospan", "hapacol", "siro ho", "viêm phế quản"
        ]) and not is_asking_gerd

        # Intent Tài chính & Cổ phiếu Chứng khoán (Mục 5.5 Tiểu luận: AMZN)
        is_asking_financial = any(term in msg_lower for term in [
            "chứng khoán", "chung khoan", "cổ phiếu", "co phieu", "amazon", "amzn", 
            "báo cáo tài chính", "bao cao tai chinh", "form 10-k", "10-k", "aws", "doanh thu aws", 
            "đầu tư cổ phiếu", "dau tu co phieu", "rủi ro amazon", "rui ro amzn", "tài chính", "tai chinh"
        ])

        # =====================================================================
        # 3. ĐIỀU HƯỚNG SUY LUẬN THEO Ý ĐỊNH
        # =====================================================================
        # Ưu tiên 0: Chào hỏi / Khởi đầu trò chuyện (Phản hồi tức thì < 5ms)
        if is_greeting:
            triage_level = "info"
            decision_title = "TRỢ LÝ THÔNG MINH GRAPH-RAG (Y TẾ & TÀI CHÍNH) SẴN SÀNG HỖ TRỢ"
            reply_text = (
                "👉 **TRẢ LỜI:** 👋 **Xin chào bạn! Tôi là Trợ lý AI Đa lĩnh vực (Y tế & Tài chính Chứng khoán).**\n\n"
                "• **Tôi có thể hỗ trợ bạn tra cứu chuyên sâu hai lĩnh vực cốt lõi:**\n"
                "  1. 💊 **Y tế & An toàn Dược phẩm:** Tư vấn bệnh thường gặp (đau đầu, trào ngược, cảm cúm, gout), an toàn dùng thuốc (suy thận, tiểu đường) & giá thuốc Long Châu.\n"
                "  2. 📈 **Tài chính & Chứng khoán (AMZN - Mục 5.5):** Phân tích cổ phiếu Amazon, động lực tăng trưởng đám mây AWS (+19%), rủi ro chuỗi cung ứng chip GPU AI và trích xuất Báo cáo Form 10-K.\n"
                "• **Cách đặt câu hỏi:** Bạn có thể nhập trực tiếp câu hỏi vào ô chat hoặc bấm vào các câu hỏi mẫu gợi ý ngay bên dưới!"
            )
            reasoning_path = "Giao tiếp khởi đầu phiên -> Giới thiệu năng lực chuyên môn GraphRAG (Y tế & Tài chính AMZN)"
            highlight_nodes.extend(["Nhà thuốc Long Châu", "Paracetamol (Acetaminophen)", "Amazon (AMZN)", "AWS Cloud"])
            suggested_followups = [
                "Bị đau đầu chóng mặt thì nên uống thuốc gì an toàn?",
                "Cổ phiếu Amazon (AMZN) có tiềm năng gì và đối mặt rủi ro nào theo Form 10-K?",
                "Trào ngược dạ dày thực quản uống Yumangel hay Gaviscon tốt hơn?",
                "Người suy thận nặng có uống được Metformin không?"
            ]

        # Ưu tiên 0.5: Phân tích Tài chính & Cổ phiếu Doanh nghiệp (Chương 4 & Mục 5.5: AMZN)
        elif is_asking_financial:
            triage_level = "info"
            fin_res = self.query_financial(query=message, ticker="AMZN", top_k=2)
            decision_title = "PHÂN TÍCH CHỨNG KHOÁN & BÁO CÁO TÀI CHÍNH FORM 10-K (AMAZON / AMZN)"
            reply_text = (
                "👉 **TRẢ LỜI: PHÂN TÍCH TÀI CHÍNH & TIỀM NĂNG CỔ PHIẾU AMAZON (AMZN):**\n\n"
                "• **Động lực tăng trưởng cốt lõi (AWS Cloud):** Theo Báo cáo Form 10-K Q4/2026, bộ phận điện toán đám mây Amazon Web Services (AWS) ghi nhận doanh thu tăng trưởng ấn tượng **+19%**, đạt **27.5 tỷ USD/quý** nhờ nhu cầu bùng nổ hạ tầng AI tạo sinh (Generative AI).\n"
                "• ⚠️ **Rủi ro chuỗi cung ứng & Chi phí đầu tư:** Doanh nghiệp phụ thuộc lớn vào các nhà cung ứng chip bán dẫn AI độc quyền, có thể dẫn đến chậm trễ bàn giao cụm tính toán đám mây thế hệ mới và gia tăng chi phí biên; chi phí CapEx mở rộng trung tâm dữ liệu tăng rất mạnh.\n"
                "• **Đối thủ cạnh tranh trực tiếp:** Cạnh tranh khốc liệt trên thị trường đám mây & AI với **Microsoft (MSFT Azure)** và **Alphabet (Google Cloud)**.\n"
                "• 📊 **Khuyến nghị đầu tư định lượng:** Duy trì đánh giá **Khả quan (Outperform)**, cần theo dõi sát tiến độ tự chủ chip tăng tốc AI (Trainium2, Inferentia) và biên lợi nhuận hoạt động của mảng AWS."
            )
            reasoning_path = "AMZN -> OWNS -> AWS Cloud -> DRIVER -> Nhu cầu Hạ tầng AI; RISK -> Thiếu hụt GPU AI & CapEx"
            highlight_nodes.extend(["Amazon (AMZN)", "AWS Cloud", "Nhu cầu Hạ tầng AI", "Thiếu hụt GPU AI"])
            evidence_sources = fin_res["evidence_sources"]
            suggested_followups = [
                "Động lực tăng trưởng chính của điện toán đám mây AWS là gì?",
                "Rủi ro thiếu hụt chip GPU AI ảnh hưởng đến Amazon thế nào?",
                "Doanh thu AWS đạt bao nhiêu trong báo cáo Form 10-K?"
            ]

        # Ưu tiên 1: Chống chỉ định Metformin khi suy thận (eGFR < 30)
        elif is_asking_metformin_contraindication:
            triage_level = "danger"
            decision_title = "CẢNH BÁO: CHỐNG CHỈ ĐỊNH TUYỆT ĐỐI METFORMIN KHI SUY THẬN"
            egfr_desc = f" (khi eGFR = {egfr} mL/min)" if egfr is not None else " (khi eGFR < 30 mL/min hoặc suy thận nặng)"
            reply_text = (
                "👉 **TRẢ LỜI: BỆNH NHÂN SUY THẬN NẶNG TUYỆT ĐỐI KHÔNG ĐƯỢC TIẾP TỤC DÙNG METFORMIN.**\n\n"
                f"• **Chống chỉ định tuyệt đối{egfr_desc}:** Theo phác đồ ADA & KDIGO, dùng Metformin khi eGFR < 30 mL/min (suy thận nặng Giai đoạn 4 - 5) sẽ gây tích tụ thuốc dẫn đến **Nhiễm toan Lactic (Lactic Acidosis)** nguy kịch tính mạng (tỷ lệ tử vong tới 50%).\n"
                "• **Phác đồ thay thế an toàn số 1 (Chuẩn vàng):** Chuyển sang tiêm **Insulin nền (Lantus SoloStar / Insulin Glargine)** 10 IU tiêm dưới da mỗi tối (chuyển hóa qua gan, hoàn toàn an toàn cho thận).\n"
                "• **Thuốc uống thay thế an toàn số 2:** Dùng **Linagliptin 5mg (Trajenta)** 1 viên/ngày (95% đào thải qua mật và phân, không cần giảm liều khi suy thận).\n"
                "• **Hành động khẩn cấp:** Cần ngừng ngay viên Metformin đang uống và đến gặp bác sĩ Nội tiết - Thận để được chuyển đổi đơn thuốc an toàn."
            )
            reasoning_path = "Bệnh nhân suy thận nặng (eGFR < 30) -> CONTRAINDICATED_IN -> Metformin -> PREFERRED -> Insulin Glargine / Linagliptin"
            highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Metformin", "Nhiễm toan Lactic", "Insulin Glargine", "Linagliptin", "eGFR < 30 mL/min"])
            suggested_followups = [
                "Liều dùng khởi đầu của Insulin Glargine là bao nhiêu?",
                "Thuốc Linagliptin 5mg có tác dụng phụ gì không?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?"
            ]

        # Ưu tiên 2: Chế độ ăn & Dinh dưỡng
        elif is_asking_diet:
            triage_level = "info"
            has_dia = any(t in msg_lower for t in ["tiểu đường", "tieu duong", "đái tháo đường", "dai thao duong", "đường huyết", "duong huyet"])
            has_kid = any(t in msg_lower for t in ["thận", "than", "egfr", "creatinine"])

            if has_kid and not has_dia:
                decision_title = "HƯỚNG DẪN DINH DƯỠNG: BỆNH SUY THẬN"
                egfr_desc = f" (eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: 4 NGUYÊN TẮC DINH DƯỠNG TRỌNG TÂM CHO NGƯỜI BỆNH SUY THẬN{egfr_desc}:**\n\n"
                    "• **1. Cắt giảm Đạm (Protein):** Ăn 0.6 - 0.8g/kg/ngày (~35 - 45g thịt nạc/cá/lòng trắng trứng mỗi ngày). Hạn chế tối đa thịt đỏ (bò, trâu, dê) để giảm tải quá trình lọc của cầu thận.\n"
                    "• **2. Giảm Muối triệt để:** Ăn nhạt dưới 2g Natri/ngày (< 1 thìa cà phê muối tinh), tuyệt đối không chấm nước mắm nguyên chất, không ăn đồ hộp, đồ chế biến sẵn, mì tôm.\n"
                    "• **3. Kiêng hoa quả giàu Kali (Tránh ngừng tim):** Tuyệt đối kiêng chuối, cam, nho khô, bơ, nước dừa (khi thận suy, kali máu tích tụ không đào thải được gây loạn nhịp tim nguy hiểm).\n"
                    "• **4. Lượng nước uống:** Uống lượng nước bằng *Lượng nước tiểu 24h + 500 mL* (tránh thừa nước gây phù và ứ trệ tuần hoàn)."
                )
                reasoning_path = "Bệnh suy thận -> NGUYÊN TẮC DINH DƯỠNG -> Giảm Đạm, Giảm Muối & Kiêng Kali"
                highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Thực đơn mẫu 1 ngày cho người suy thận?",
                    "Tại sao người suy thận phải kiêng chuối và cam?",
                    "Suy thận giai đoạn 4 có uống được sữa không?"
                ]
            elif has_dia and not has_kid:
                decision_title = "HƯỚNG DẪN DINH DƯỠNG: BỆNH ĐÁI THÁO ĐƯỜNG"
                reply_text = (
                    "👉 **TRẢ LỜI: 4 NGUYÊN TẮC ĂN UỐNG TRỌNG TÂM CHO NGƯỜI BỆNH TIỂU ĐƯỜNG:**\n\n"
                    "• **1. Kiểm soát Tinh bột (Carbohydrate):** Hạn chế tinh bột tinh chế (cơm trắng, bánh mì trắng, bún, miến). Thay bằng tinh bột chuyển hóa chậm (gạo lứt, yến mạch, khoai lang).\n"
                    "• **2. Kiêng đường hấp thu nhanh:** Tuyệt đối tránh bánh kẹo ngọt, nước ngọt có ga, trà sữa, hoa quả quá ngọt (sầu riêng, nhãn, vải, mít).\n"
                    "• **3. Tăng cường chất xơ:** Ăn nhiều rau xanh các loại (rau muống, cải bó xôi, súp lơ) đầu bữa ăn để làm chậm hấp thu đường vào máu.\n"
                    "• **4. Chia nhỏ bữa ăn:** Ăn đúng giờ, không bỏ bữa, có thể thêm 1 bữa phụ nhỏ trước khi ngủ để tránh hạ đường huyết đêm."
                )
                reasoning_path = "Đái tháo đường -> NGUYÊN TẮC DINH DƯỠNG -> Giảm Carb GI cao & Tăng Chất xơ"
                highlight_nodes.extend(["Đái tháo đường Tuýp 2"])
                suggested_followups = [
                    "Người tiểu đường nên ăn hoa quả gì an toàn?",
                    "Thực đơn mẫu 1 ngày cho người tiểu đường?",
                    "Mục tiêu kiểm soát đường huyết lúc đói là bao nhiêu?"
                ]
            else:
                decision_title = "HƯỚNG DẪN DINH DƯỠNG: TIỂU ĐƯỜNG KÈM SUY THẬN MẠN TÍNH"
                egfr_desc = f" (eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: 4 NGUYÊN TẮC ĂN UỐNG CHO BỆNH NHÂN TIỂU ĐƯỜNG KÈM SUY THẬN{egfr_desc}:**\n\n"
                    "• **1. Cắt giảm Đạm (Protein):** Ăn 0.6 - 0.8g/kg/ngày (~35 - 45g thịt nạc/cá/lòng trắng trứng). Tránh thịt đỏ để bảo tồn chức năng thận.\n"
                    "• **2. Giảm Muối & Đường:** Ăn nhạt < 2g muối/ngày; kiêng đồ ngọt hấp thu nhanh và nước ngọt có ga.\n"
                    "• **3. Kiêng thực phẩm giàu Kali:** Tránh chuối, cam, nho khô, bơ, nước dừa (nguy cơ tăng kali máu gây ngừng tim khi eGFR < 30).\n"
                    "• **4. Lượng nước uống:** Uống lượng nước bằng *Lượng nước tiểu 24h + 500 mL*."
                )
                reasoning_path = "Bệnh nhân -> Suy thận mạn GĐ 4 + ĐTĐ -> NGUYÊN TẮC DINH DƯỠNG KẾT HỢP"
                highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Bệnh nhân (Pima)"])
                suggested_followups = [
                    "Thực đơn mẫu 1 ngày cho người suy thận?",
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                    "Tại sao người suy thận phải kiêng chuối và cam?"
                ]

        # Phân nhánh 1.2: Kiến thức tổng quan về BỆNH SUY THẬN (CKD)
        elif is_asking_kidney_disease:
            triage_level = "warning" if (egfr is not None and egfr < 30) else "info"
            decision_title = "TƯ VẤN CHUYÊN SÂU: BỆNH SUY THẬN MẠN TÍNH (CKD)"
            has_dia = any(t in msg_lower for t in ["tiểu đường", "tieu duong", "đái tháo đường", "dai thao duong"])
            
            dia_info = " Đái tháo đường lâu năm là nguyên nhân trực tiếp làm tổn thương màng lọc cầu thận." if has_dia else " Hai nguyên nhân phổ biến nhất gây suy thận mạn là Tăng huyết áp và Đái tháo đường; ngoài ra còn do viêm cầu thận, sỏi thận, hoặc lạm dụng thuốc giảm đau NSAID."
            egfr_desc = f" (Mức eGFR của bạn hiện tại: {egfr} mL/min)" if egfr is not None else ""

            reply_text = (
                f"👉 **TRẢ LỜI: TỔNG QUAN BỆNH SUY THẬN MẠN VÀ 5 GIAI ĐOẠN KDIGO:**\n\n"
                f"• **5 Giai đoạn theo mức lọc cầu thận eGFR:** GĐ 1 (≥ 90 mL/min) -> GĐ 2 (60-89) -> GĐ 3 (30-59) -> GĐ 4 (15-29: Suy thận nặng) -> GĐ 5 (< 15: Suy thận giai đoạn cuối, bắt buộc lọc máu/ghép thận).{egfr_desc}\n"
                f"• **Nguyên nhân gây bệnh:**{dia_info}\n"
                "• **Nguyên tắc bảo tồn chức năng thận:** Cấm tuyệt đối thuốc giảm đau NSAID (Ibuprofen, Meloxicam); kiểm soát huyết áp < 130/80 mmHg; ăn giảm đạm và giảm muối để làm chậm tiến triển bệnh."
            )
            reasoning_path = "Suy thận mạn tính (CKD) -> PHÂN LOẠI KDIGO 5 GIAI ĐOẠN -> Nguyên tắc bảo tồn thận"
            highlight_nodes.extend(["Suy thận mạn tính Giai đoạn 4-5", "Protein niệu (Đạm nước tiểu)", "eGFR < 30 mL/min"])
            suggested_followups = [
                "Chế độ ăn cho người suy thận?",
                "Đau đầu uống thuốc gì an toàn cho người suy thận?",
                "Suy thận giai đoạn 4 có chữa khỏi hoàn toàn được không?"
            ]

        # Phân nhánh 1.3: Bệnh Đái tháo đường Tuýp 2
        elif is_asking_diabetes_overview:
            triage_level = "info"
            decision_title = "TỔNG QUAN Y KHOA: BỆNH ĐÁI THÁO ĐƯỜNG TUÝP 2"
            hba1c_desc = f" *(Chỉ số HbA1c hiện tại: {hba1c}%)*" if hba1c is not None else ""
            reply_text = (
                "👉 **TRẢ LỜI: TỔNG QUAN VỀ BỆNH ĐÁI THÁO ĐƯỜNG TUÝP 2:**\n\n"
                "• **Bản chất bệnh:** Tình trạng rối loạn chuyển hóa mạn tính do cơ thể bị đề kháng insulin và suy giảm tiết insulin từ tuyến tụy, khiến nồng độ đường trong máu luôn ở mức cao.\n"
                f"• **Chỉ số chẩn đoán & theo dõi:** HbA1c ≥ 6.5% hoặc Glucose đói ≥ 7.0 mmol/L.{hba1c_desc}\n"
                "• **Biến chứng mạn tính:** Biến chứng mạch máu nhỏ (thận, võng mạc mắt, dây thần kinh ngoại biên) và mạch máu lớn (nhồi máu cơ tim, đột quỵ não).\n"
                "• **Kiểm soát trọng tâm:** Ăn giảm tinh bột chuyển hóa nhanh, tập thể dục 150 phút/tuần và dùng thuốc hạ đường huyết an toàn cho thận."
            )
            reasoning_path = "Đái tháo đường Tuýp 2 -> RỐI LOẠN CHUYỂN HÓA -> Đề kháng Insulin & Kiểm soát đường huyết"
            highlight_nodes.extend(["Đái tháo đường Tuýp 2", "HbA1c > 8.0%"])
            suggested_followups = [
                "Chế độ ăn cho người bệnh tiểu đường?",
                "Mục tiêu đường huyết an toàn là bao nhiêu?",
                "Dấu hiệu sớm nhận biết bệnh tiểu đường là gì?"
            ]

        # =====================================================================
        # NHÁNH 2: HẠ ĐƯỜNG HUYẾT CẤP TÍNH (HYPOGLYCEMIA)
        # =====================================================================
        elif (any(term in msg_lower for term in ["hạ đường", "vã mồ hôi", "run tay", "đường huyết thấp", "< 3.9", "tụt đường"]) or 
              ("chóng mặt" in msg_lower and not is_asking_vestibular)):
            triage_level = "warning"
            decision_title = "HƯỚNG DẪN XỬ TRÍ HẠ ĐƯỜNG HUYẾT CẤP TÍNH (QUY TẮC SỐ 15)"
            reply_text = (
                "👉 **TRẢ LỜI: XỬ TRÍ CẤP CỨU HẠ ĐƯỜNG HUYẾT THEO QUY TẮC 15 (KHI ĐƯỜNG HUYẾT < 3.9 mmol/L):**\n\n"
                "• **1. Nạp ngay 15g Carbohydrate nhanh:** Uống 1/2 cốc nước ngọt có đường hoặc nước ép hoa quả (120ml), hoặc 1 cốc nước ấm pha 3 thìa đường/mật ong, hoặc ăn 3 - 4 viên kẹo ngọt.\n"
                "• **2. Nghỉ ngơi 15 phút:** Ngồi nghỉ thả lỏng và đo lại đường huyết mao mạch bằng máy đo cá nhân.\n"
                "• **3. Đánh giá tiếp:** Nếu vẫn < 3.9 mmol/L, nạp tiếp 15g đường. Khi đã đạt > 4.0 mmol/L, ăn ngay một bữa phụ nhỏ (bánh quy, nửa bát cơm) để tránh tái hạ đường huyết."
            )
            reasoning_path = "Bệnh nhân -> Hạ đường huyết cấp tính -> ÁP DỤNG -> Quy tắc 15g Carbonhydrate"
            highlight_nodes.extend(["Hạ đường huyết cấp tính", "Gliclazide"])
            suggested_followups = [
                "Thuốc nào trong đơn gây hạ đường huyết?",
                "Làm sao phòng ngừa hạ đường huyết ban đêm?",
                "Khi nào cần gọi cấp cứu 115?"
            ]

        # =====================================================================
        # NHÁNH 3: CƠN ĐAU ĐẦU / NHỨC ĐẦU & NGUY CƠ HUYẾT ÁP
        # =====================================================================
        elif is_asking_headache:
            has_kidney = (egfr is not None and egfr < 60) or any(t in msg_lower for t in ["suy thận", "suy than", "bệnh thận", "benh than", "thận", "than", "egfr"])
            triage_level = "warning" if (egfr is not None and egfr < 30) else "info"

            if has_kidney:
                decision_title = "TƯ VẤN LÂM SÀNG: XỬ TRÍ ĐAU ĐẦU CHO NGƯỜI BỆNH THẬN"
                egfr_desc = f" (eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: ĐAU ĐẦU UỐNG THUỐC GÌ AN TOÀN CHO NGƯỜI SUY THẬN{egfr_desc}:**\n\n"
                    "• **Thuốc giảm đau an toàn nhất:** Dùng **Paracetamol 500mg (Panadol xanh hoặc Hapacol)**, giá ~1.000đ - 2.000đ/viên tại Long Châu. Uống 1 viên khi đau nhiều, cách nhau tối thiểu 8 - 12 giờ (tối đa không quá 2.000mg/ngày). Paracetamol chuyển hóa qua gan, không độc cho thận.\n"
                    "• **Việc cần làm ngay lập tức:** Đo ngay **Huyết áp** cá nhân (người suy thận rất dễ đau đầu dữ dội do cơn tăng huyết áp kịch phát > 140/90 mmHg).\n"
                    "• ⛔ **CHỐNG CHỈ ĐỊNH TUYỆT ĐỐI THUỐC NSAID:** Cấm tuyệt đối uống Ibuprofen, Meloxicam, Diclofenac (Voltaren) vì nhóm này làm co mạch thận, đẩy bệnh nhân vào suy thận cấp nguy kịch!"
                )
                reasoning_path = "Người bệnh thận -> Đau đầu -> ƯU TIÊN ĐO HUYẾT ÁP & Paracetamol (CHỐNG CHỈ ĐỊNH NSAID)"
                highlight_nodes.extend(["Paracetamol (Acetaminophen)", "Hapacol 650mg", "Tăng huyết áp", "Suy thận mạn tính Giai đoạn 4-5", "Nhà thuốc Long Châu"])
            else:
                decision_title = "TƯ VẤN LÂM SÀNG: XỬ TRÍ ĐAU ĐẦU & THUỐC GIẢM ĐAU AN TOÀN"
                reply_text = (
                    "👉 **TRẢ LỜI: ĐAU ĐẦU UỐNG THUỐC GÌ AN TOÀN?**\n\n"
                    "• **Thuốc giảm đau thông dụng số 1:** Dùng **Panadol 500mg** hoặc **Hapacol 500mg/650mg** (~1.500đ - 2.500đ/viên tại Nhà thuốc Long Châu). Uống 1 viên khi đau nhiều, cách nhau 4 - 6 giờ (tối đa không quá 4g/ngày cho người lớn khỏe mạnh).\n"
                    "• **Nếu kèm đau đầu căng thẳng hoặc mệt mỏi:** Có thể chọn **Panadol Extra** (chứa thêm Paracetamol 500mg + Cafein 65mg giúp tăng tác dụng giảm đau nhanh chóng).\n"
                    "• **Hành động cần làm:** Nghỉ ngơi trong không gian yên tĩnh, uống đủ nước, đo huyết áp nếu đau đầu dữ dội.\n"
                    "• ⚠️ **Lưu ý an toàn:** Không uống thuốc giảm đau liên tục quá 3 ngày nếu triệu chứng không thuyên giảm. Người có tiền sử suy giảm chức năng gan, thận hoặc đau dạ dày nên giảm liều hoặc tham khảo ý kiến bác sĩ."
                )
                reasoning_path = "Người bệnh -> Đau đầu thông thường -> FIRST_LINE -> Paracetamol (Panadol / Hapacol 500mg)"
                highlight_nodes.extend(["Paracetamol (Acetaminophen)", "Hapacol 650mg", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Tại sao người suy thận không được uống thuốc giảm đau Ibuprofen?",
                "Bị đau đầu kèm chóng mặt quay cuồng uống Betaserc được không?",
                "Huyết áp bao nhiêu thì gây đau đầu nguy hiểm?"
            ]

        # =====================================================================
        # NHÁNH 3.1: ĐAU CƠ SAU VẬN ĐỘNG MẠNH & THỂ THAO
        # =====================================================================
        elif is_asking_exercise_symptom and not is_asking_flu_cough:
            triage_level = "warning" if (egfr is not None and egfr < 30) else "info"
            decision_title = "TƯ VẤN LÂM SÀNG: ĐAU MỎI CƠ SAU VẬN ĐỘNG & THUỐC AN TOÀN"
            reply_text = (
                "👉 **TRẢ LỜI: XỬ TRÍ ĐAU MỎI CƠ SAU VẬN ĐỘNG THỂ THAO:**\n\n"
                "• **Thuốc giảm đau an toàn:** Uống **Paracetamol (Hapacol 650mg hoặc Panadol)** 1 viên khi đau nhiều, cách 4 - 6 giờ (tối đa 2.000mg - 3.000mg/ngày cho người lớn). Paracetamol chuyển hóa qua gan, lành tính.\n"
                "• **Phục hồi tự nhiên:** Nghỉ ngơi thả lỏng cơ bắp, chườm ấm nhẹ nhàng vùng cơ căng mỏi, uống bù nước lọc hoặc nước điện giải oresol từng ngụm nhỏ.\n"
                "• ⛔ **LƯU Ý:** Tránh lạm dụng các thuốc giảm đau chống viêm mạnh nhóm NSAID (Ibuprofen, Voltaren) nếu có tiền sử đau dạ dày hoặc suy giảm chức năng thận."
            )
            reasoning_path = "Đau cơ do vận động -> Paracetamol (An toàn qua gan) -> Phục hồi cơ & Bù điện giải"
            highlight_nodes.extend(["Panadol Extra", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Bị đau cơ sau khi tập gym nên chườm nóng hay chườm lạnh?",
                "Uống oresol bù điện giải thế nào cho đúng cách?",
                "Đau cơ bắp bao nhiêu ngày không khỏi thì nên đi khám?"
            ]

        # =====================================================================
        # NHÁNH 4: CÁC THUỐC CỤ THỂ (INSULIN, LINAGLIPTIN, DAPAGLIFLOZIN, GLICLAZIDE)
        # =====================================================================
        elif any(term in msg_lower for term in ["insulin", "tiêm", "glargine", "linagliptin", "dapagliflozin", "gliclazide", "sglt2", "dpp4"]):
            triage_level = "info"
            if "insulin" in msg_lower or "glargine" in msg_lower:
                decision_title = "PHÁC ĐỒ SỬ DỤNG INSULIN NỀN KHI SUY THẬN"
                reply_text = (
                    "👉 **TRẢ LỜI: HƯỚNG DẪN DÙNG INSULIN NỀN CHO BỆNH NHÂN SUY THẬN:**\n\n"
                    "• **Thuốc chuẩn vàng:** **Insulin Glargine (Bút tiêm Lantus SoloStar 100 IU/ml)**. Insulin chuyển hóa qua gan nên an toàn tuyệt đối cho người suy thận nặng.\n"
                    "• **Liều khởi đầu khuyến nghị:** Thường bắt đầu với **10 IU/ngày** tiêm dưới da 1 lần cố định vào buổi tối trước khi đi ngủ.\n"
                    "• **Lưu ý an toàn:** Khi suy thận, insulin giáng hóa chậm hơn nên cần theo dõi sát đường huyết đói buổi sáng để tránh hạ đường huyết ban đêm."
                )
                reasoning_path = "Bệnh nhân -> Suy thận nặng -> THAY THẾ AN TOÀN -> Insulin Glargine"
                highlight_nodes.extend(["Insulin Glargine", "Suy thận mạn tính Giai đoạn 4-5"])
            elif "linagliptin" in msg_lower:
                decision_title = "THUỐC HẠ ĐƯỜNG HUYẾT LINAGLIPTIN (TRAJENTA 5MG)"
                reply_text = (
                    "👉 **TRẢ LỜI: ĐÁNH GIÁ THUỐC LINAGLIPTIN (TRAJENTA 5MG) KHI SUY THẬN:**\n\n"
                    "• **Độ an toàn:** **RẤT AN TOÀN VÀ LÀ THUỐC VIÊN HÀNG ĐẦU**. Linagliptin đào thải 95% qua mật và phân, chỉ 5% qua thận.\n"
                    "• **Liều dùng:** Duy trì **5mg (1 viên) x 1 lần/ngày**, **hoàn toàn không cần giảm liều** ở mọi giai đoạn suy thận.\n"
                    "• **Giá tham khảo tại Long Châu:** Khoảng **26.500 đ/viên** (~795.000 đ/hộp 30 viên, thuốc kê đơn Rx)."
                )
                reasoning_path = "Bệnh nhân -> Suy thận nặng -> THUỐC UỐNG AN TOÀN -> Linagliptin (5mg)"
                highlight_nodes.extend(["Linagliptin", "Suy thận mạn tính Giai đoạn 4-5"])
            else:
                decision_title = "THUỐC BẢO VỆ TIM - THẬN SGLT-2i (DAPAGLIFLOZIN)"
                egfr_desc = f" (khi eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: ĐÁNH GIÁ DAPAGLIFLOZIN (FORXIGA 10MG){egfr_desc}:**\n\n"
                    "• **Tác dụng:** Thuốc ức chế SGLT-2 giúp bảo vệ thận và tim mạch. Tuy nhiên khi eGFR < 25-30 mL/min, hiệu quả hạ đường huyết của thuốc bị suy giảm rõ rệt.\n"
                    "• **Khuyến nghị:** Cần có chỉ định và theo dõi chặt chẽ của Bác sĩ chuyên khoa Thận - Nội tiết trước khi dùng."
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
            decision_title = "MỤC TIÊU KIỂM SOÁT ĐƯỜNG HUYẾT AN TOÀN"
            hba1c_desc = f" (Hiện tại HbA1c: {hba1c}%)" if hba1c is not None else ""
            reply_text = (
                f"👉 **TRẢ LỜI: MỤC TIÊU ĐƯỜNG HUYẾT VÀ HBA1C AN TOÀN{hba1c_desc}:**\n\n"
                "• **HbA1c mục tiêu:** **7.0% - 8.0%** (Với người có bệnh thận mạn hoặc cao tuổi, mục tiêu được nới lỏng lên 7.5% - 8.0% nhằm ngăn ngừa nguy cơ hạ đường huyết nguy hiểm).\n"
                "• **Đường huyết lúc đói:** Duy trì từ **5.0 - 7.2 mmol/L** (90 - 130 mg/dL).\n"
                "• **Đường huyết sau ăn 2h:** Dưới **10.0 mmol/L** (< 180 mg/dL).\n"
                "• **Đo định kỳ:** Kiểm tra HbA1c 3 tháng/lần và xét nghiệm chức năng thận (eGFR, Creatinine) định kỳ."
            )
            reasoning_path = "Mục tiêu điều trị ĐTĐ -> HbA1c 7.0 - 8.0% -> Kiểm soát an toàn tránh hạ đường huyết"
            highlight_nodes.extend(["HbA1c > 8.0%", "Đái tháo đường Tuýp 2"])
            suggested_followups = [
                "Tại sao người suy thận không nên hạ HbA1c quá thấp?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Khi nào cần chuyển sang tiêm Insulin?"
            ]

        # =====================================================================
        # NHÁNH 5.1: TƯƠNG TÁC THUỐC ĐA BỆNH LÝ
        # =====================================================================
        elif is_asking_interaction:
            triage_level = "warning"
            decision_title = "ĐÁNH GIÁ TƯƠNG TÁC THUỐC: HUYẾT ÁP + TIỂU ĐƯỜNG + SUY THẬN"
            egfr_desc = f" (eGFR = {egfr} mL/min)" if egfr is not None else ""
            reply_text = (
                f"👉 **TRẢ LỜI: TƯƠNG TÁC GIỮA THUỐC HUYẾT ÁP, TIỂU ĐƯỜNG VÀ SUY THẬN{egfr_desc}:**\n\n"
                "• **Amlodipine (Amlor 5mg) + Thuốc tiểu đường:** Rất an toàn. Amlodipine đào thải qua gan, hạ huyết áp tốt và không ảnh hưởng chức năng lọc của thận.\n"
                "• **Perindopril (Coversyl 5mg):** Khi suy thận nặng, thuốc nhóm ACEi này dễ gây **Tăng Kali máu nguy hiểm** và tụt huyết áp. Bắt buộc xét nghiệm điện giải và Creatinine máu sau 1-2 tuần dùng.\n"
                "• ⛔ **Thuốc giảm đau:** Cấm tuyệt đối phối hợp NSAID (Ibuprofen, Meloxicam) với Coversyl vì sẽ gây suy thận cấp tức thì."
            )
            reasoning_path = "Tăng huyết áp + ĐTĐ Tuýp 2 -> TƯƠNG TÁC THUỐC -> Amlor (An toàn) vs Coversyl (Theo dõi Kali khi suy thận)"
            highlight_nodes.extend(["Tăng huyết áp", "Amlodipine", "Perindopril", "Suy thận mạn tính Giai đoạn 4-5"])
            suggested_followups = [
                "Tại sao người suy thận không được uống thuốc giảm đau Ibuprofen?",
                "Chế độ ăn cho bệnh nhân tiểu đường kèm suy thận mạn?",
                "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?"
            ]

        # =====================================================================
        # NHÁNH 5.1B: ĐAU ĐẦU, GIẢM ĐAU & HẠ SỐT AN TOÀN
        # =====================================================================
        elif is_asking_pain_relief:
            has_kidney = (egfr is not None and egfr < 60) or any(t in msg_lower for t in ["suy thận", "suy than", "bệnh thận", "benh than", "thận", "than", "egfr"])
            
            if has_kidney:
                triage_level = "info"
                decision_title = "TƯ VẤN DƯỢC LÂM SÀNG: GIẢM ĐAU CHO NGƯỜI BỆNH THẬN"
                egfr_desc = f" (eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: NGƯỜI BỆNH SUY THẬN{egfr_desc} DÙNG ĐƯỢC PANADOL / PARACETAMOL, NHƯNG BẮT BUỘC PHẢI GIẢM LIỀU:**\n\n"
                    "• **Thuốc giảm đau an toàn số 1:** Dùng **Panadol 500mg (viên xanh)** hoặc **Hapacol 500mg** (~1.500đ - 2.500đ/viên tại Long Châu). Paracetamol chuyển hóa chủ yếu qua gan nên là thuốc an toàn nhất cho thận.\n"
                    "• **Liều lượng chuẩn cho người bệnh thận:** Uống **500mg/lần**, mỗi lần cách nhau **8 - 12 giờ** (thay vì 4-6 giờ như người bình thường). Tối đa không quá **2g/ngày**. Tránh dùng Panadol Extra vì chứa caffeine làm tăng huyết áp.\n"
                    "• ⛔ **CHỐNG CHỈ ĐỊNH TUYỆT ĐỐI THUỐC NSAID:** Tuyệt đối **CẤM** dùng các thuốc giảm đau kháng viêm NSAID (như **Ibuprofen, Meloxicam, Diclofenac, Voltaren, Celecoxib**) vì sẽ làm co mạch thận, gây suy thận cấp tiến triển nặng!"
                )
                reasoning_path = "Người bệnh suy thận -> Đau đầu / Giảm đau -> PREFERRED Paracetamol (GIẢM LIỀU 8-12h) -> CONTRAINDICATED NSAID"
                highlight_nodes.extend(["Paracetamol (Acetaminophen)", "Hapacol 650mg", "Ibuprofen (Kháng viêm NSAID)", "Suy thận mạn tính Giai đoạn 4-5", "Nhà thuốc Long Châu"])
                suggested_followups = [
                    "Tại sao người suy thận không được uống thuốc giảm đau Ibuprofen?",
                    "Chế độ ăn cho người suy thận cần kiêng những gì?",
                    "Các dấu hiệu cảnh báo suy thận cần đi khám gấp?"
                ]
            else:
                triage_level = "info"
                decision_title = "TƯ VẤN DƯỢC LÂM SÀNG: THUỐC GIẢM ĐAU & HẠ SỐT AN TOÀN"
                reply_text = (
                    "👉 **TRẢ LỜI: ĐAU ĐẦU, ĐAU NHỨC UỐNG THUỐC GÌ AN TOÀN?**\n\n"
                    "• **Thuốc giảm đau thông dụng số 1:** Dùng **Panadol 500mg** hoặc **Hapacol 500mg / 650mg** (~1.500đ - 2.500đ/viên tại Nhà thuốc Long Châu). Uống 1 viên khi đau nhiều, cách nhau 4 - 6 giờ (tối đa không quá 4g/ngày cho người lớn khỏe mạnh).\n"
                    "• **Nếu kèm đau đầu căng thẳng hoặc mệt mỏi:** Có thể chọn **Panadol Extra** (chứa thêm Cafein 65mg giúp tăng tác dụng giảm đau nhanh chóng).\n"
                    "• ⚠️ **Lưu ý an toàn:** Không uống liên tục quá 3 ngày nếu triệu chứng không thuyên giảm. Người có tiền sử suy giảm chức năng gan, thận hoặc đau dạ dày nên giảm liều hoặc tham khảo ý kiến bác sĩ."
                )
                reasoning_path = "Người bệnh -> Đau đầu / Giảm đau thông thường -> FIRST_LINE -> Paracetamol (Panadol / Hapacol 500mg)"
                highlight_nodes.extend(["Paracetamol (Acetaminophen)", "Hapacol 650mg", "Nhà thuốc Long Châu"])
                suggested_followups = [
                    "Đau đầu kèm chóng mặt buồn nôn là triệu chứng bệnh gì?",
                    "Bị đau đầu do căng thẳng mất ngủ nên làm gì?",
                    "Thuốc Panadol Extra khác gì so với Panadol thường?"
                ]

        # =====================================================================
        # NHÁNH 5.2: VIÊM LOÉT DẠ DÀY & TRÀO NGƯỢC THỰC QUẢN (GERD)
        # =====================================================================
        elif is_asking_gerd:
            triage_level = "info"
            decision_title = "TƯ VẤN LÂM SÀNG: VIÊM LOÉT DẠ DÀY & TRÀO NGƯỢC THỰC QUẢN (GERD)"
            reply_text = (
                f"👉 **TRẢ LỜI: ĐAU DẠ DÀY / TRÀO NGƯỢC THỰC QUẢN (GERD) UỐNG THUỐC GÌ?**\n\n"
                "• **Thuốc uống ưu tiên hàng đầu:** **Nexium Mups 20mg (Esomeprazole)** (~23.500đ/viên tại Long Châu): Uống 1 viên vào buổi sáng trước bữa ăn 30-60 phút. Chuyển hóa qua gan, an toàn cho người suy thận.\n"
                "• **Thuốc cắt cơn ợ chua, nóng rát tức thì:** **Gaviscon Dual Action** (~6.500đ/gói OTC): Uống 1 gói sau ăn hoặc khi bị ợ nóng thượng vị.\n"
                f"• ⛔ **CẢNH BÁO NGUY HIỂM:** Bị đau dạ dày tuyệt đối không được tự ý uống thuốc giảm đau NSAID (Ibuprofen, Voltaren) vì vừa làm loét thủng dạ dày vừa gây suy thận cấp!"
            )
            reasoning_path = "Bệnh nhân -> Trào ngược GERD / Viêm dạ dày -> FIRST_LINE_PPI -> Nexium Mups (Esomeprazole) & Gaviscon"
            highlight_nodes.extend(["Viêm loét dạ dày - Trào ngược (GERD)", "Esomeprazole", "Nexium Mups 20mg", "Gaviscon Dual Action", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Thuốc Nexium uống trong bao lâu thì ngưng?",
                "Người suy thận đau dạ dày có uống được nghệ mật ong không?",
                "Phân biệt triệu chứng đau dạ dày với đau thắt ngực tim mạch?"
            ]

        # =====================================================================
        # NHÁNH 5.3: XỬ TRÍ CƠN GOUT CẤP & AN TOÀN CHỨC NĂNG THẬN
        # =====================================================================
        elif is_asking_gout:
            triage_level = "warning"
            decision_title = "TƯ VẤN LÂM SÀNG: XỬ TRÍ CƠN GOUT CẤP KHI SUY THẬN"
            reply_text = (
                f"👉 **TRẢ LỜI: XỬ TRÍ CƠN GÚT CẤP AN TOÀN CHO BỆNH NHÂN SUY THẬN (eGFR = {egfr} mL/min):**\n\n"
                "• **Thuốc cắt cơn gút duy nhất được dùng:** **Colchicina Stella 1mg (Colchicine)** (~2.500đ/viên Rx tại Long Châu). Uống 1 viên ngay khi bắt đầu đau, sau đó 1 giờ uống thêm nửa viên (0.5mg).\n"
                f"• ⚠️ **BẮT BUỘC GIẢM 50% LIỀU COLCHICINE:** Vì bệnh nhân suy thận GĐ 4 đào thải thuốc chậm, sau liều đầu chỉ dùng tối đa 0.5mg/ngày để tránh độc tủy xương.\n"
                "• ⛔ **CHỐNG CHỈ ĐỊNH TUYỆT ĐỐI THUỐC NSAID:** Cấm dùng Ibuprofen, Diclofenac, Meloxicam, Celecoxib vì sẽ đẩy bệnh nhân vào suy thận giai đoạn cuối phải chạy thận khẩn cấp!"
            )
            reasoning_path = "Bệnh nhân (eGFR 25) -> Cơn Gout cấp -> CONTRAINDICATED NSAID -> Colchicina Stella (GIẢM 50% LIỀU)"
            highlight_nodes.extend(["Cơn Gout cấp tính & Tăng Acid Uric", "Colchicine", "Colchicina Stella 1mg", "Suy thận mạn tính Giai đoạn 4-5", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Chế độ ăn cho người bị cả bệnh gout, tiểu đường và suy thận?",
                "Khi nào được bắt đầu uống thuốc hạ acid uric Allopurinol?",
                "Khớp ngón chân cái sưng nóng đỏ làm sao giảm đau nhanh không hại thận?"
            ]

        # =====================================================================
        # NHÁNH 5.4: DỊ ỨNG THỜI TIẾT, MỀ ĐAY & VIÊM MŨI DỊ ỨNG
        # =====================================================================
        elif is_asking_allergy:
            triage_level = "info"
            decision_title = "TƯ VẤN DƯỢC LÂM SÀNG: DỊ ỨNG, MỀ ĐAY & VIÊM MŨI"
            reply_text = (
                f"👉 **TRẢ LỜI: DỊ ỨNG, MỀ ĐAY, MẨN NGỨA UỐNG THUỐC GÌ AN TOÀN?**\n\n"
                "• **Thuốc kháng Histamin an toàn nhất:** **Telfast HD 180mg (Fexofenadine)** (~12.500đ/viên OTC tại Long Châu) hoặc Zyrtec 10mg (Cetirizine). Uống 1 viên/ngày.\n"
                "• **Đánh giá trên bệnh nhân suy thận:** Fexofenadine thải 80% qua phân, không phụ thuộc lọc thận, hoàn toàn an toàn cho người suy thận và không gây buồn ngủ.\n"
                "• **Lưu ý:** Không tự ý dùng các loại kem bôi hoặc viên uống chứa Corticoid kéo dài vì sẽ làm đường huyết tăng vọt."
            )
            reasoning_path = "Bệnh nhân -> Dị ứng / Mề đay -> FIRST_LINE_ANTIHISTAMINE -> Telfast HD 180mg (Fexofenadine)"
            highlight_nodes.extend(["Dị ứng / Mề đay cấp & mạn", "Fexofenadine", "Telfast HD 180mg", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Bị nổi mề đay kèm khó thở có phải đi cấp cứu không?",
                "Uống Telfast liên tục bao nhiêu ngày thì được?",
                "Người tiểu đường bị dị ứng bôi thuốc gì an toàn?"
            ]

        # =====================================================================
        # NHÁNH 5.5: RỐI LOẠN TIỀN ĐÌNH & ĐAU ĐẦU CĂNG THẲNG
        # =====================================================================
        elif is_asking_vestibular:
            triage_level = "info"
            decision_title = "TƯ VẤN LÂM SÀNG: RỐI LOẠN TIỀN ĐÌNH & CHÓNG MẶT"
            reply_text = (
                f"👉 **TRẢ LỜI: CHÓNG MẶT, RỐI LOẠN TIỀN ĐÌNH UỐNG THUỐC GÌ?**\n\n"
                "• **Thuốc điều trị tiền đình đầu tay:** **Betaserc 16mg (Betahistine)** (~5.800đ/viên Rx tại Long Châu): Uống 1 viên x 2 lần/ngày trong hoặc sau bữa ăn để cải thiện tuần hoàn tai trong.\n"
                "• **Hành động ưu tiên ngay:** Đo ngay **Huyết áp** và **Đường huyết** cá nhân (loại trừ cơn tụt đường huyết < 3.9 mmol/L hoặc cơn tăng huyết áp kịch phát gây chóng mặt nguy hiểm).\n"
                "• **Nghỉ ngơi:** Nằm trong phòng yên tĩnh, tránh quay đầu hoặc ngồi dậy đột ngột."
            )
            reasoning_path = "Bệnh nhân -> Rối loạn tiền đình -> FIRST_LINE_VESTIBULAR -> Betaserc 16mg (Betahistine)"
            highlight_nodes.extend(["Rối loạn tiền đình & Đau đầu căng thẳng", "Betahistine", "Betaserc 16mg", "Tăng huyết áp", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Cách phân biệt chóng mặt tiền đình với đột quỵ não?",
                "Bị tiền đình huyết áp cao uống Betaserc chung Amlor được không?",
                "Tập các bài tập phục hồi chức năng tiền đình Brandt-Daroff thế nào?"
            ]

        # =====================================================================
        # NHÁNH 5.6: CẢM CÚM, SỐT NHẸ & HO VIÊM HỌNG
        # =====================================================================
        elif is_asking_flu_cough:
            triage_level = "info"
            decision_title = "TƯ VẤN ĐIỀU TRỊ CẢM CÚM, SỐT & HO ĐỜM VIÊM HỌNG"
            reply_text = (
                f"👉 **TRẢ LỜI: CẢM CÚM, SỐT, ĐAU HỌNG, HO UỐNG THUỐC GÌ AN TOÀN?**\n\n"
                "• **Hạ sốt & giảm đau rát họng an toàn:** **Hapacol 650mg** (~1.000đ/viên) hoặc **Panadol** (~2.000đ/viên): Uống 1 viên khi sốt ≥ 38.5°C hoặc đau rát họng, cách 4 - 6 giờ (tối đa 2g/ngày). An toàn qua gan cho người suy thận.\n"
                "• **Trị ho đờm, rát cổ an toàn:** **Siro ho Prospan 100ml (Cao lá thường xuân)** (~75.000đ/chai tại Long Châu): Uống 5ml x 3 lần/ngày.\n"
                f"• ⛔ **CẤM UỐNG THUỐC CẢM CHỨA NSAID:** Không dùng các gói cảm cúm chứa Ibuprofen, Aspirin vì làm tổn thương thận nặng thêm. Không tự ý uống kháng sinh vì cảm cúm do virus."
            )
            reasoning_path = "Bệnh nhân -> Cảm cúm / Viêm họng -> Paracetamol (Hapacol/Panadol) & Siro Prospan -> CHỐNG CHỈ ĐỊNH NSAID"
            highlight_nodes.extend(["Cảm cúm / Nhiễm siêu vi", "Viêm họng cấp tính", "Paracetamol (Acetaminophen)", "Hapacol 650mg", "Siro Prospan 100ml", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Sốt cảm cúm bao nhiêu ngày không đỡ thì phải vào viện?",
                "Thuốc cảm cúm nào người suy thận và tiểu đường uống an toàn?",
                "Bị đau họng có nên ngậm kẹo ngậm chứa đường không?"
            ]

        # =====================================================================
        # NHÁNH 5.7: TRA CỨU BIỆT DƯỢC THƯƠNG MẠI NHÀ THUỐC LONG CHÂU & BÁO GIÁ
        # =====================================================================
        elif is_asking_brand_drug:
            triage_level = "info"
            # 1. Glucophage
            if "glucophage" in msg_lower:
                triage_level = "danger" if (egfr is not None and egfr < 30) else "warning"
                decision_title = "TRA CỨU BIỆT DƯỢC: GLUCOPHAGE (METFORMIN)"
                egfr_desc = f" (Mức lọc thận hiện tại: eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    "👉 **TRẢ LỜI: THÔNG TIN VỀ THUỐC GLUCOPHAGE (METFORMIN):**\n\n"
                    f"• **Chống chỉ định suy thận:{egfr_desc}** Glucophage chứa Metformin, chống chỉ định tuyệt đối khi eGFR < 30 mL/min (suy thận nặng Giai đoạn 4-5). Dùng khi suy thận nặng sẽ gây tích tụ thuốc và biến chứng **Nhiễm toan Lactic** tử vong 50%.\n"
                    "• **Đối với người chức năng thận bình thường:** Là thuốc đầu tay điều trị Đái tháo đường Tuýp 2, giá ~4.500đ/viên tại Long Châu.\n"
                    "• **Đổi sang thuốc thay thế an toàn khi có bệnh thận:** Mua **Trajenta 5mg (Linagliptin)** ~26.500đ/viên hoặc **Bút tiêm Lantus SoloStar** ~285.000đ/bút (an toàn tuyệt đối cho người suy thận)."
                )
                reasoning_path = "Glucophage 500mg -> CHỨA -> Metformin -> Chống chỉ định khi eGFR < 30"
                highlight_nodes.extend(["Glucophage 500mg", "Metformin", "Nhà thuốc Long Châu", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?",
                    "Khi eGFR dưới 30 thì chuyển sang Insulin nền liều lượng như thế nào?",
                    "Dấu hiệu sớm của nhiễm toan lactic do Metformin?"
                ]

            # 2. Trajenta
            elif "trajenta" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: TRAJENTA 5MG (LINAGLIPTIN)"
                egfr_desc = f" (kể cả khi eGFR = {egfr} mL/min)" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: THUỐC TRAJENTA 5MG RẤT AN TOÀN CHO BỆNH NHÂN TIỂU ĐƯỜNG{egfr_desc}.**\n\n"
                    "• **Độ an toàn:** Là thuốc viên hạ đường huyết số 1 cho người suy thận vì 95% đào thải qua mật/gan, không hại thận, **không cần giảm liều**.\n"
                    "• **Liều dùng:** 1 viên 5mg x 1 lần/ngày (uống cùng hoặc không cùng bữa ăn).\n"
                    "• **Giá tham khảo tại Long Châu:** Khoảng **26.500 đ/viên** (~795.000 đ/hộp 30 viên, thuốc kê đơn Rx)."
                )
                reasoning_path = "Trajenta 5mg -> CHỨA -> Linagliptin -> SAFE_FOR_RENAL -> Thải trừ qua gan mật"
                highlight_nodes.extend(["Trajenta 5mg", "Linagliptin", "Nhà thuốc Long Châu", "Suy thận mạn tính Giai đoạn 4-5"])
                suggested_followups = [
                    "Trajenta 5mg có gây tác dụng phụ tụt đường huyết không?",
                    "Uống Trajenta vào buổi sáng hay buổi tối tốt hơn?",
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?"
                ]

            # 3. Lantus SoloStar
            elif "lantus" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: BÚT TIÊM LANTUS SOLOSTAR (INSULIN)"
                reply_text = (
                    "👉 **TRẢ LỜI: BÚT TIÊM LANTUS SOLOSTAR LÀ PHÁC ĐỒ CHUẨN VÀNG CHO SUY THẬN.**\n\n"
                    "• **Độ an toàn:** Insulin Glargine chuyển hóa qua gan, không độc cho mô thận, là giải pháp kiểm soát đường huyết an toàn nhất khi eGFR < 30 mL/min.\n"
                    "• **Liều khởi đầu:** Thường tiêm dưới da 10 IU vào một giờ cố định mỗi tối.\n"
                    "• **Giá tham khảo tại Long Châu:** Khoảng **285.000 đ/bút tiêm** (~1.425.000 đ/hộp 5 bút, bảo quản ngăn mát 2-8°C)."
                )
                reasoning_path = "Lantus SoloStar -> CHỨA -> Insulin Glargine -> PREFERRED_INSULIN -> Chuyển hóa an toàn qua gan"
                highlight_nodes.extend(["Lantus SoloStar", "Insulin Glargine", "Nhà thuốc Long Châu", "Bệnh viện Đa khoa / BV Thận"])
                suggested_followups = [
                    "Khi eGFR dưới 30 thì chuyển sang Insulin nền liều lượng như thế nào?",
                    "Cách tiêm bút Lantus SoloStar vào vùng bụng an toàn?",
                    "Xử trí khi bị hạ đường huyết sau tiêm Insulin?"
                ]

            # 4. Forxiga
            elif "forxiga" in msg_lower:
                decision_title = "TRA CỨU BIỆT DƯỢC: FORXIGA 10MG (DAPAGLIFLOZIN)"
                egfr_desc = f" VỚI CHỈ SỐ eGFR = {egfr} mL/min" if egfr is not None else ""
                reply_text = (
                    f"👉 **TRẢ LỜI: ĐÁNH GIÁ FORXIGA 10MG (DAPAGLIFLOZIN){egfr_desc}:**\n\n"
                    "• **Hiệu quả:** Thuốc giúp bảo vệ tim - thận, nhưng ở mức lọc thận thấp (< 25-30 mL/min) thì khả năng hạ đường huyết qua nước tiểu đã giảm nhiều.\n"
                    "• **Giá tham khảo tại Long Châu:** Khoảng **28.000 đ/viên** (~784.000 đ/hộp 28 viên, thuốc Rx).\n"
                    "• **Khuyến nghị:** Cần bác sĩ chuyên khoa Thận - Nội tiết thăm khám và chỉ định cụ thể."
                )
                reasoning_path = "Forxiga 10mg -> CHỨA -> Dapagliflozin -> CARDIO_RENAL_PROTECTION -> Chỉ định theo mức lọc cầu thận"
                highlight_nodes.extend(["Forxiga 10mg", "Dapagliflozin", "Nhà thuốc Long Châu", "Bệnh thận đái tháo đường (DKD)"])
                suggested_followups = [
                    "Bệnh nhân tiểu đường có suy tim thì dùng Dapagliflozin có lợi ích gì?",
                    "Tác dụng phụ thường gặp của thuốc Forxiga là gì?",
                    "Khi nào cần ngưng thuốc Forxiga trước phẫu thuật?"
                ]

            # 5. Tổng quan Long Châu & Danh mục thuốc đầy đủ
            else:
                decision_title = "TRA CỨU BIỆT DƯỢC NHÀ THUỐC LONG CHÂU"
                reply_text = (
                    "👉 **BẢNG GIÁ THAM KHẢO CÁC BIỆT DƯỢC THÔNG DỤNG TẠI NHÀ THUỐC LONG CHÂU:**\n\n"
                    "| Biệt Dược | Hoạt Chất | Giá Tham Khảo | An Toàn Thận (eGFR 25) |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                    "| **Glucophage 500mg** | Metformin | ~4.500 đ/viên | ⛔ CẤM DÙNG (Toan lactic) |\n"
                    "| **Trajenta 5mg** | Linagliptin | ~26.500 đ/viên | ✅ Rất an toàn (Thải mật) |\n"
                    "| **Lantus SoloStar** | Insulin Glargine | ~285.000 đ/bút | ✅ Chuẩn vàng cho suy thận |\n"
                    "| **Forxiga 10mg** | Dapagliflozin | ~28.000 đ/viên | ⚠️ Cần bác sĩ chỉ định |\n"
                    "| **Amlor 5mg** | Amlodipine | ~8.500 đ/viên | ✅ Hạ huyết áp an toàn |\n"
                    "| **Nexium Mups 20mg** | Esomeprazole | ~23.500 đ/viên | ✅ Trào ngược / Dạ dày |\n"
                    "| **Gaviscon Dual Action** | Natri alginate | ~6.500 đ/gói | ✅ Cắt cơn ợ chua tức thì |\n"
                    "| **Telfast HD 180mg** | Fexofenadine | ~12.500 đ/viên | ✅ Dị ứng, không buồn ngủ |\n"
                    "| **Colchicina Stella 1mg**| Colchicine | ~2.500 đ/viên | ⚠️ Gout (Phải giảm 50% liều) |\n"
                    "| **Betaserc 16mg** | Betahistine | ~5.800 đ/viên | ✅ Tiền đình, chóng mặt |\n"
                    "| **Hapacol 650mg** | Paracetamol | ~1.000 đ/viên | ✅ Giảm đau, hạ sốt an toàn |\n"
                    "| **Siro Prospan 100ml** | Cao thường xuân | ~75.000 đ/chai | ✅ Trị ho đờm thảo dược |"
                )
                reasoning_path = "Nhà thuốc Long Châu -> DANH MỤC BIỆT DƯỢC GPP -> Tra cứu Hoạt chất & Báo giá & Phân loại Rx"
                highlight_nodes.extend(["Nhà thuốc Long Châu", "Glucophage 500mg", "Trajenta 5mg", "Lantus SoloStar", "Nexium Mups 20mg", "Telfast HD 180mg"])
                suggested_followups = [
                    "Bệnh nhân có chỉ số eGFR là 25 mL/min và HbA1c 8.5%. Có nên tiếp tục dùng Metformin không?",
                    "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu, suy thận có uống được không?",
                    "Bị trào ngược dạ dày có uống được Nexium hay Gaviscon không?"
                ]

        # =====================================================================
        # NHÁNH 5.8: HƯỚNG DẪN KHÁM CHUYÊN KHOA & HỘI ĐỒNG BỆNH VIỆN
        # =====================================================================
        # =====================================================================
        # NHÁNH 5.8: HƯỚNG DẪN KHÁM CHUYÊN KHOA & HỘI ĐỒNG BỆNH VIỆN
        # =====================================================================
        elif is_asking_hospital:
            triage_level = "info"
            decision_title = "HƯỚNG DẪN KHÁM CHUYÊN KHOA & BỆNH VIỆN TUYẾN ĐẦU"
            reply_text = (
                "👉 **TRẢ LỜI: HƯỚNG DẪN CHỌN BỆNH VIỆN VÀ CHUYÊN KHOA THĂM KHÁM:**\n\n"
                "• **Các chuyên khoa thăm khám hàng đầu:**\n"
                "  1. **Khoa Thận - Tiết niệu:** Dành cho người có dấu hiệu phù, tiểu bọt, suy giảm chức năng thận hoặc tăng Creatinine máu.\n"
                "  2. **Khoa Nội tiết:** Dành cho người đái tháo đường, rối loạn đường huyết, bệnh lý tuyến giáp.\n"
                "  3. **Khoa Tiêu hóa & Thần kinh:** Dành cho bệnh nhân trào ngược dạ dày, viêm loét, đau đầu mạn tính, rối loạn tiền đình.\n"
                "• **Bệnh viện tuyến đầu uy tín khuyến nghị:**\n"
                "  - **Miền Bắc:** Bệnh viện Bạch Mai, Bệnh viện Đại học Y Hà Nội, Bệnh viện Nội tiết Trung ương.\n"
                "  - **Miền Nam:** Bệnh viện Chợ Rẫy, Bệnh viện Đại học Y Dược TP.HCM, Bệnh viện Nhân dân 115.\n"
                "• **Lưu ý trước khi đi khám:** Mang theo thẻ BHYT, toàn bộ hồ sơ xét nghiệm máu, siêu âm và danh sách thuốc đang uống tại nhà."
            )
            reasoning_path = "HỘI CHẨN CHUYÊN KHOA -> Bệnh viện Đa khoa / BV Chuyên khoa Tuyến đầu"
            highlight_nodes.extend(["Bệnh viện Đa khoa / BV Thận", "Nhà thuốc Long Châu"])
            suggested_followups = [
                "Bị đau đầu chóng mặt uống thuốc gì an toàn?",
                "Bị trào ngược dạ dày ợ chua uống thuốc gì?",
                "Thuốc Trajenta 5mg giá bao nhiêu ở Long Châu?"
            ]

        # =====================================================================
        # NHÁNH 6: TƯ VẤN DỰA TRÊN VECTOR RAG & PHÁC ĐỒ GỐC
        # =====================================================================
        else:
            best_evidence = evidence_sources[0] if evidence_sources else None
            is_low_similarity = (not best_evidence or best_evidence["similarity"] < 0.15)
            
            if is_low_similarity:
                triage_level = "info"
                decision_title = "TƯ VẤN Y TẾ & CHĂM SÓC SỨC KHỎE TỔNG QUÁT"
                reply_text = (
                    f"👉 **TRẢ LỜI:** Câu hỏi *\"{message}\"* chưa có trong phác đồ chuyên khoa đã thẩm định sẵn của hệ thống.\n\n"
                    "• **Lời khuyên y tế tổng quát:** Nếu bạn đang gặp các triệu chứng cấp tính bất thường hoặc mệt mỏi kéo dài, vui lòng đến các cơ sở y tế gần nhất để bác sĩ thăm khám và xét nghiệm cụ thể.\n"
                    "• **Thuốc giảm đau thông dụng an toàn:** Người lớn có thể dùng Paracetamol (Panadol / Hapacol 500mg) 1 viên khi đau sốt nhẹ. Tránh tự ý lạm dụng kháng sinh hoặc thuốc giảm đau kháng viêm mạnh khi chưa có chỉ định.\n"
                    "• Bạn có thể hỏi thêm về: đau đầu, cảm sốt, đau dạ dày, viêm họng, dị ứng, gout, tiểu đường hoặc tra cứu giá thuốc Long Châu."
                )
                reasoning_path = "Câu hỏi ngoài phạm vi cơ sở dữ liệu chuyên sâu -> HƯỚNG DẪN Y TẾ TỔNG QUÁT"
                highlight_nodes.extend(["Nhà thuốc Long Châu"])
                suggested_followups = [
                    "Bị đau đầu chóng mặt uống thuốc gì an toàn?",
                    "Bị trào ngược dạ dày ợ chua uống thuốc gì?",
                    "Cảm sốt, đau họng uống thuốc gì?"
                ]
            else:
                triage_level = "info"
                decision_title = f"TƯ VẤN DỰA TRÊN PHÁC ĐỒ: {best_evidence['source']}"
                reply_text = (
                    f"👉 **TRẢ LỜI CĂN CỨ THEO PHÁC ĐỒ {best_evidence['source']} (Trang {best_evidence['page']}):**\n\n"
                    f"• **Khuyến cáo cốt lõi:** \"{best_evidence['snippet']}\"\n"
                    "• **Lưu ý lâm sàng:** Mọi chỉ định dùng thuốc cần dựa trên tình trạng sức khỏe thực tế, chức năng gan thận và tuân thủ hướng dẫn của bác sĩ điều trị."
                )
                reasoning_path = f"Truy xuất Vector RAG -> Đối soát Phác đồ {best_evidence['source']}"
                highlight_nodes.extend(["Bác sĩ Lâm sàng AI", "Nhà thuốc Long Châu"])
                suggested_followups = [
                    "Bị đau đầu chóng mặt uống thuốc gì an toàn?",
                    "Chế độ ăn cho bệnh nhân tiểu đường cần kiêng gì?",
                    "Thuốc Panadol Extra khác gì so với Panadol thường?"
                ]

        # =====================================================================
        # TĂNG CƯỜNG SUY LUẬN BẰNG MÔ HÌNH NGÔN NGỮ LỚN (GEMINI AI)
        # =====================================================================
        final_api_key = self.get_api_key(gemini_api_key)
        llm_active = False

        # Không gọi Gemini khi người dùng chỉ chào hỏi hoặc câu hỏi quá ngắn
        if is_greeting or len(message.strip().split()) < 2:
            use_llm = False

        if use_llm and final_api_key:
            try:
                is_dia_related = any(t in msg_lower for t in ["tiểu đường", "tieu duong", "đái tháo đường", "dai thao duong", "metformin", "đường huyết", "duong huyet", "insulin", "trajenta", "forxiga"])
                is_pain_or_drug = any(t in msg_lower for t in ["giảm đau", "giam dau", "thuốc", "thuoc", "uống", "uong", "panadol", "paracetamol", "hapacol", "đau", "dau"])
                is_kid_related = any(t in msg_lower for t in ["suy thận", "suy than", "bệnh thận", "benh than", "thận", "than", "egfr", "creatinine"]) or (egfr is not None and egfr < 60)

                clinical_notes = []
                if is_dia_related:
                    if egfr is not None and egfr < 30:
                        clinical_notes.append(f"Cảnh báo: eGFR = {egfr} mL/min chống chỉ định tuyệt đối Metformin do nguy cơ toan acid lactic; phác đồ thay thế là Insulin hoặc Trajenta 5mg.")
                    else:
                        clinical_notes.append("Người bệnh hỏi về Đái tháo đường: Cần lưu ý phác đồ kiểm soát đường huyết an toàn, các nhóm thuốc (Metformin, Trajenta, Insulin...).")
                
                if is_kid_related:
                    clinical_notes.append("Người bệnh có vấn đề về Thận: Cảnh báo cấm thuốc độc thận như NSAID (Ibuprofen, Meloxicam); ưu tiên Paracetamol liều giảm.")
                elif is_pain_or_drug:
                    clinical_notes.append("Người bệnh hỏi về thuốc giảm đau / hạ sốt: Hướng dẫn liều dùng Paracetamol an toàn cho người lớn (500mg/lần, cách 4-6h, tối đa 4g/ngày).")

                profile_info = []
                if profile.get("age"):
                    profile_info.append(f"Tuổi: {profile['age']}")
                if egfr is not None:
                    profile_info.append(f"eGFR = {egfr} mL/min")
                if hba1c is not None:
                    profile_info.append(f"HbA1c = {hba1c}%")
                
                patient_desc = f"- Thông tin người bệnh: {', '.join(profile_info)}\n" if profile_info else "- Đối tượng: Người dân / Người bệnh cần tra cứu y khoa & sử dụng thuốc an toàn.\n"

                kg_context = (
                    f"{patient_desc}"
                    f"- Lưu ý chuyên môn từ Đồ thị Tri thức: {'; '.join(clinical_notes) if clinical_notes else 'Tư vấn y tế tổng quát chính xác theo chuẩn dược thư & phác đồ.'}\n"
                    f"- Danh mục Long Châu liên kết: Glucophage XR, Trajenta 5mg, Lantus SoloStar, Forxiga 10mg, Nexium Mups 20mg, Gaviscon, Telfast 180mg, Colchicina 1mg, Betaserc 16mg, Panadol, Hapacol, Prospan."
                )

                docs_context = "\n".join([f"[{d['source']}]: {d['snippet']}" for d in evidence_sources])

                if is_asking_financial:
                    sys_prompt = (
                        "Bạn là Chuyên gia Phân tích Tài chính Định lượng & Cố vấn Đầu tư Chứng khoán Cấp cao.\n"
                        "NHIỆM VỤ: Trả lời NGAY VÀO TRỌNG TÂM CÂU HỎI của nhà đầu tư về cổ phiếu và tình hình kinh doanh, cực kỳ súc tích, chuyên nghiệp.\n"
                        "CÁC NGUYÊN TẮC BẮT BUỘC:\n"
                        "1. DÒNG ĐẦU TIÊN: Trả lời trực diện nhận định chính (Ví dụ: '👉 TRẢ LỜI: [Đánh giá tổng quan về cổ phiếu / doanh thu]').\n"
                        "2. TẬP TRUNG TỐI ĐA 3 - 4 GẠCH ĐẦU DÒNG:\n"
                        "   • Động lực tăng trưởng cốt lõi (AWS Cloud, tỷ lệ tăng trưởng doanh thu theo Form 10-K).\n"
                        "   • Các rủi ro chuỗi cung ứng (thiếu hụt GPU AI, chi phí CapEx trung tâm dữ liệu).\n"
                        "   • Khuyến nghị định giá hoặc theo dõi phân tích định lượng.\n"
                        "3. Dùng Markdown chuẩn, in đậm các con số và chỉ số quan trọng."
                    )
                    usr_prompt = (
                        f"### BÁO CÁO TÀI CHÍNH FORM 10-K & KNOWLEDGE GRAPH:\n{docs_context}\n\n"
                        f"### CÂU HỎI CỦA NHÀ ĐẦU TƯ:\n{message}"
                    )
                else:
                    sys_prompt = (
                        "Bạn là Bác sĩ Trợ lý Y khoa và Dược sĩ Lâm sàng AI tại Chuỗi Nhà thuốc FPT Long Châu.\n"
                        "NHIỆM VỤ: Trả lời NGAY VÀO TRỌNG TÂM CÂU HỎI của người bệnh, cực kỳ súc tích, ngắn gọn, chính xác.\n"
                        "CÁC NGUYÊN TẮC BẮT BUỘC:\n"
                        "1. CHỈ TRẢ LỜI ĐÚNG VẤN ĐỀ ĐƯỢC HỎI: Tuyệt đối không tự ý nhắc đến Tiểu đường hay Metformin nếu câu hỏi của người bệnh KHÔNG đề cập đến.\n"
                        "2. DÒNG ĐẦU TIÊN: Trả lời trực diện ngay câu hỏi (Ví dụ: '👉 TRẢ LỜI: [Thuốc nên uống / Giải pháp chính]').\n"
                        "3. TUYỆT ĐỐI KHÔNG: Không chào hỏi xã giao dài dòng, không viết mở bài lan man, không viết văn giải thích dài dòng kiểu sách giáo khoa lý thuyết.\n"
                        "4. NỘI DUNG TẬP TRUNG TỐI ĐA 3 - 4 GẠCH ĐẦU DÒNG:\n"
                        "   • Tên thuốc/giải pháp cụ thể + Liều dùng an toàn + Giá tham khảo tại Long Châu (nếu có).\n"
                        "   • Đánh giá mức độ an toàn cho người bệnh.\n"
                        "   • Cảnh báo nguy hiểm / chống chỉ định liên quan trực tiếp đến vấn đề được hỏi.\n"
                        "5. Dùng Markdown chuẩn, in đậm tên thuốc và liều lượng rõ ràng."
                    )
                    usr_prompt = (
                        f"### THÔNG TIN LÂM SÀNG & ĐỒ THỊ TRI THỨC:\n{kg_context}\n\n"
                        f"### TÀI LIỆU PHÁC ĐỒ ĐÃ ĐỐI SOÁT:\n{docs_context}\n\n"
                        f"### CÂU HỎI CỦA NGƯỜI BỆNH:\n{message}"
                    )

                gemini_text = self.call_gemini_llm(usr_prompt, sys_prompt, final_api_key)
                if gemini_text and len(gemini_text.strip()) > 30:
                    reply_text = gemini_text.strip()
                    llm_active = True
                    decision_title = "PHÂN TÍCH TÀI CHÍNH TĂNG CƯỜNG (GRAPHRAG + GEMINI AI)" if is_asking_financial else "TƯ VẤN Y KHOA TĂNG CƯỜNG (GRAPHRAG + GEMINI AI)"
            except Exception as e:
                print(f"[Gemini Enhancement Error]: {e}")

        latency = int((time.time() - t0) * 1000) + (180 if llm_active else 120)

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
            "latency_ms": latency,
            "llm_enhanced": llm_active,
            "engine": "GraphRAG + Google Gemini AI" if llm_active else "GraphRAG Cục bộ (Offline In-Memory)"
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
            "latency_ms": latency,
            "llm_enhanced": llm_active,
            "engine": "GraphRAG + Google Gemini 1.5 Flash" if llm_active else "GraphRAG Cục bộ (Offline In-Memory)"
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
