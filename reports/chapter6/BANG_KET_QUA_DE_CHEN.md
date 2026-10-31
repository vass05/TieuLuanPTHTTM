# Bảng kết quả Chương 6 để chèn tài liệu

Giữ CSV gốc để đối chiếu. Giá trị ± là SD qua seed trên cùng split. Precision@3 chia cho k=3 dù ngưỡng chỉ trả về ít hơn ba tài liệu; có một tài liệu liên quan/câu. Hỗ trợ trích xuất kiểm tra tóm tắt/ID, không phải faithfulness ngữ nghĩa.

## Bảng 6.1. Đặc trưng và dữ liệu thiếu của Pima

Mục 6.4.1, trang 163–164 của v3.

| Đặc trưng | Đơn vị | 0 là thiếu | Số giá trị thiếu | Nhỏ nhất | Lớn nhất |
| --- | --- | --- | --- | --- | --- |
| Pregnancies | count | Không | 0 | 0.0000 | 17.0000 |
| Glucose | mg/dL | Có | 5 | 44.0000 | 199.0000 |
| BloodPressure | mmHg | Có | 35 | 24.0000 | 122.0000 |
| SkinThickness | mm | Có | 227 | 7.0000 | 99.0000 |
| Insulin | uU/mL | Có | 374 | 14.0000 | 846.0000 |
| BMI | kg/m2 | Có | 11 | 18.2000 | 67.1000 |
| DiabetesPedigreeFunction | score | Không | 0 | 0.0780 | 2.4200 |
| Age | years | Không | 0 | 21.0000 | 81.0000 |

## Bảng 6.2. Chia tập độc lập

Mục 6.6.1, trang 171–172 của v3.

| Tập | Số trường hợp | Nhãn 0 | Nhãn 1 | Tỷ lệ |
| --- | --- | --- | --- | --- |
| train | 491 | 320 | 171 | 0.6393 |
| validation | 123 | 80 | 43 | 0.1602 |
| test | 154 | 100 | 54 | 0.2005 |

## Bảng 6.3. Phân loại trên test: trung bình và độ lệch chuẩn qua 5 seed

Mục 6.6.2, trang 172–174 của v3.

| Mô hình | Accuracy | Precision | Recall | F1 | ROC-AUC | AP / PR-AUC | Brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Logistic Regression | 0.7143 ± 0.0000 | 0.5962 ± 0.0000 | 0.5741 ± 0.0000 | 0.5849 ± 0.0000 | 0.8161 ± 0.0000 | 0.6808 ± 0.0000 | 0.1747 ± 0.0000 |
| MLP PyTorch | 0.7429 ± 0.0149 | 0.6083 ± 0.0204 | 0.7519 ± 0.0248 | 0.6722 ± 0.0159 | 0.8093 ± 0.0058 | 0.6655 ± 0.0145 | 0.1715 ± 0.0022 |
| Random Forest | 0.7390 ± 0.0116 | 0.6189 ± 0.0199 | 0.6778 ± 0.1274 | 0.6408 ± 0.0553 | 0.8176 ± 0.0029 | 0.6745 ± 0.0137 | 0.1650 ± 0.0016 |

## Bảng 6.4. Truy xuất trên 20 câu hỏi có bằng chứng và 4 câu ngoài miền

Mục 6.6.3, trang 174 của v3.

| Phương pháp | Precision@3 | Recall@3 | Hit@3 | Từ chối ngoài miền | Bao phủ dẫn nguồn | Hỗ trợ trích xuất | TB (ms) | P95 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid | 0.3167 | 0.9500 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 0.9149 | 1.0983 |
| LSA | 0.3167 | 0.9500 | 0.9500 | 0.0000 | 1.0000 | 1.0000 | 1.3684 | 1.8099 |
| TF-IDF | 0.3000 | 0.9000 | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 0.6320 | 1.0115 |

## Bảng 6.5. Chọn ngưỡng truy xuất trên validation (10 câu có bằng chứng, 2 câu ngoài miền)

Mục 6.4.2, trang 165–166 của v3.

| Phương pháp | Ngưỡng | Mục tiêu validation |
| --- | --- | --- |
| TF-IDF | 0.0800 | 0.5972 |
| TF-IDF | 0.1500 | 0.8889 |
| TF-IDF | 0.2500 | 1.0000 |
| TF-IDF | 0.3500 | 0.6667 |
| LSA | 0.0800 | 0.4167 |
| LSA | 0.1500 | 0.4167 |
| LSA | 0.2500 | 0.4167 |
| LSA | 0.3500 | 0.4583 |
| Hybrid | 0.0800 | 0.7222 |
| Hybrid | 0.1500 | 0.9444 |
| Hybrid | 0.2500 | 1.0000 |
| Hybrid | 0.3500 | 0.8333 |

## Bảng 6.6. Đối sánh chính sách trên cùng 600 kịch bản test, 5 seed

Mục 6.6.4, trang 175–176 của v3.

| Chỉ số | Q-learning | Random(valid) | Rule-Based |
| --- | --- | --- | --- |
| Reward (TB ± SD) | 4.4519 ± 0.0000 | 2.1234 ± 0.0849 | 4.4519 ± 0.0000 |
| Hoàn thành (%) (TB ± SD) | 100.00 ± 0.00 | 98.23 ± 0.67 | 100.00 ± 0.00 |
| Số bước trung bình | 2.0200 | 3.8900 | 2.0200 |
| Lần gọi công cụ trung bình | 1.0200 | 2.9077 | 1.0200 |
| Chi phí mô phỏng trung bình | 2.0433 | 5.7937 | 2.0433 |
| Vi phạm thực thi (%) | 0.00 | 0.00 | 0.00 |

## Bảng 6.7. Độ nhạy siêu tham số trên validation mô phỏng

Mục 6.7.6, trang 179 của v3.

| Learning rate α | Epsilon decay | Reward TB | Reward SD | Tỷ lệ hoàn thành |
| --- | --- | --- | --- | --- |
| 0.0500 | 0.9700 | 4.4955 | 0.0000 | 1.0000 |
| 0.0500 | 0.9950 | 4.4955 | 0.0000 | 1.0000 |
| 0.0500 | 0.9990 | 4.4955 | 0.0000 | 1.0000 |
| 0.1500 | 0.9700 | 4.4955 | 0.0000 | 1.0000 |
| 0.1500 | 0.9950 | 4.4955 | 0.0000 | 1.0000 |
| 0.1500 | 0.9990 | 4.4955 | 0.0000 | 1.0000 |
| 0.4000 | 0.9700 | 4.4955 | 0.0000 | 1.0000 |
| 0.4000 | 0.9950 | 4.4955 | 0.0000 | 1.0000 |
| 0.4000 | 0.9990 | 4.4955 | 0.0000 | 1.0000 |

## Bảng 6.8. Kịch bản chức năng A–F: 60 trường hợp cho mỗi chính sách

Mục 6.6.5, trang 176–177 của v3.

| Nhóm | Rule-Based đạt/tổng | Rule-Based TB ms | Q-learning đạt/tổng | Q-learning TB ms |
| --- | --- | --- | --- | --- |
| A | 10/10 | 5.1205 | 10/10 | 3.7458 |
| B | 10/10 | 0.0429 | 10/10 | 0.0433 |
| C | 10/10 | 3.9066 | 10/10 | 0.6189 |
| D | 10/10 | 0.0248 | 10/10 | 0.0235 |
| E | 10/10 | 1.8049 | 10/10 | 0.4922 |
| F | 10/10 | 4.6022 | 10/10 | 4.0124 |

## Bảng 6.9. Ablation theo phạm vi và chỉ số phù hợp với từng thành phần

Mục 6.6.6, trang 177 của v3.

| Cấu hình | Phạm vi đánh giá | Chỉ số | Giá trị | Số trường hợp |
| --- | --- | --- | --- | --- |
| Prediction Model | Pima test / MLP, 5 seeds | ROC-AUC | 0.8093 | 154 |
| Knowledge Retrieval | 20 positive retrieval test queries | Recall@3 | 0.9500 | 20 |
| Prediction + RAG (fixed pipeline) | 10 valid complete workflow cases (A) | Workflow completion rate | 1.0000 | 10 |
| Multi-Agent Rule | 60 functional scenarios A–F | Expected-outcome pass rate | 1.0000 | 60 |
| Multi-Agent RL | 60 functional scenarios A–F | Expected-outcome pass rate | 1.0000 | 60 |

## Bảng 6.10. Phân rã độ trễ thực đo (ms), môi trường CPU cục bộ

Mục 6.7.5, trang 179 của v3.

| Chính sách | Truy xuất / soạn phản hồi (ms) | Dự đoán (ms) | Kiểm tra (ms) | Điều phối (ms) |
| --- | --- | --- | --- | --- |
| q_learning | 0.7502 | 2.7634 | 0.0533 | 0.1788 |
| rule | 0.9775 | 3.8234 | 0.0799 | 0.2398 |
