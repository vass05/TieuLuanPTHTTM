# Ứng dụng các hệ thống thông minh

Dự án tiểu luận xây dựng website tích hợp các mô hình học máy, thị giác máy tính
và trợ lý hỏi đáp về tiểu đường. Ứng dụng sử dụng Flask theo kiến trúc MVC,
nạp các mô hình đã huấn luyện để dự đoán và truy xuất kiến thức có nguồn.

**Website demo:** [tieuluan-intelligent-systems.onrender.com](https://tieuluan-intelligent-systems.onrender.com)

## Chức năng chính

| Chức năng | Mô tả |
| --- | --- |
| Trợ lý tiểu đường | Hỏi đáp KB 174 tài liệu; dự đoán từ chỉ số bằng MLP. |
| Chuỗi thời gian | Dự báo AMZN và phụ tải điện AEP bằng LSTM. |
| Định giá nhà | Ước tính giá bất động sản bằng XGBoost. |
| Thị giác máy tính | Nhận diện thời trang (SE-CNN), chữ số viết tay (CNN). |
| Tra cứu GraphRAG | Tìm tài liệu y khoa qua văn bản và đồ thị kiến thức. |

## Công nghệ

Python, Flask, PyTorch, Keras, XGBoost, scikit-learn, NetworkX và SQLite.
Giao diện sử dụng HTML, CSS và JavaScript.

KB có nguồn quốc tế và 6 tài liệu tiếng Việt từ
[Cục Quản lý Khám, chữa bệnh – Bộ Y tế](https://daithaoduong.kcb.vn/) và
[Bệnh viện Bạch Mai](https://bachmai.gov.vn/bai-viet/tu-van-dinh-duong-cho-nguoi-benh-dai-thao-duong?id=5b0d7548-b38c-b260-a4b4-94dabfdb116b).
Các tài liệu tiếng Việt kèm URL, ngày đối chiếu và thông tin nguồn tại
[diabetes_vietnam.json](knowledge/diabetes_vietnam.json).

## Chạy cục bộ

```bash
python -m pip install -r requirements.txt
python app.py
```

Mở [http://127.0.0.1:5000](http://127.0.0.1:5000). Trọng số mô hình và KB đã có
trong repo; chatbot có thể trả lời từ dữ liệu cục bộ mà không cần API key.

## Triển khai

Website được triển khai trên **Render Free** bằng cấu hình [render.yaml](render.yaml).
Bản deploy sử dụng CPU và KB cục bộ, tắt Gemini, không cần Neo4j Aura.
Service có thể cần thời gian khởi động sau khi ngủ; lịch sử chat trên ổ đĩa tạm
có thể mất sau khi khởi động lại.

Các kết quả dự đoán phục vụ học tập và nghiên cứu; phần tiểu đường không thay thế
chẩn đoán y tế.
