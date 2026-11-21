# Ứng dụng các hệ thống thông minh

Dự án tiểu luận xây dựng website tích hợp các mô hình học máy, thị giác máy tính
và trợ lý hỏi đáp về tiểu đường. Ứng dụng sử dụng Flask theo kiến trúc MVC,
nạp các mô hình đã huấn luyện để dự đoán và truy xuất kiến thức có nguồn.

**Website demo:** [tieuluan-intelligent-systems.onrender.com](https://tieuluan-intelligent-systems.onrender.com)

## Chức năng chính

| Chức năng | Mô tả |
| --- | --- |
| Trợ lý tiểu đường | Hỏi đáp từ 399 bài web và 200 PDF. Dự đoán từ chỉ số bằng MLP. |
| Chuỗi thời gian | Dự báo AMZN và phụ tải điện AEP bằng LSTM. |
| Định giá nhà | Ước tính giá bất động sản bằng XGBoost. |
| Thị giác máy tính | Nhận diện thời trang (SE-CNN), chữ số viết tay (CNN). |
| Tra cứu GraphRAG | Tìm tài liệu y khoa qua văn bản và đồ thị kiến thức. |

## Công nghệ

Python, Flask, PyTorch, Keras, XGBoost, scikit-learn, NetworkX, Neo4j và SQLite.
Giao diện sử dụng HTML, CSS và JavaScript.

KB có 599 tài liệu gốc và 604 bản ghi bằng chứng. Kho giữ 399 bài web và có
200 PDF, gồm 100 PDF Việt Nam và 100 PDF quốc tế. Theo đơn vị xuất bản, toàn
kho có 299 nguồn Việt Nam và 300 nguồn quốc tế.
[Danh mục nguồn](knowledge/sources/catalog.json) ghi URL, đơn vị xuất bản,
trang trích dẫn và mã kiểm tra tệp. Các PDF bổ sung lưu trích đoạn nguyên ngữ
được đối chiếu tự động theo trang. Nội dung dùng cho nguyên mẫu học tập.

Các bản PDF tải về để đối chiếu nằm trong `knowledge/sources/pdf/library/`
trên máy phát triển. Repository giữ PDF Bộ Y tế dùng cho demo, kèm dữ liệu
trích xuất và URL mở PDF gốc cho toàn bộ danh mục.

## Chạy cục bộ

```bash
python -m pip install -r requirements.txt
python app.py
```

Mở [http://127.0.0.1:5000](http://127.0.0.1:5000). Trọng số mô hình và KB đã có
trong repo; chatbot có thể trả lời từ dữ liệu cục bộ mà không cần API key.

## Truy xuất từ Neo4j

1. Tạo một database riêng cho dự án trên [Neo4j Aura](https://console.neo4j.io/)
   hoặc dùng Neo4j cục bộ. Điền `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`,
   `NEO4J_DATABASE` trong `.env` theo `.env.example`. Lấy URI `neo4j+s://` và
   tên database từ Aura Console. Dùng tên database hiển thị trong mục Query.
2. Chạy lệnh nhập kho dưới đây. Lệnh cũng tái tạo file khởi tạo độc lập
   [DB_diabet.cypher](knowledge/DB_diabet.cypher) và danh mục nguồn từ cùng
   phiên bản dữ liệu. Có thể chạy file Cypher bằng Cypher Shell với `--file`.
3. Đặt `DIABETES_KB_BACKEND=neo4j`, chạy Flask và mở `/agents`. API `/api/v1/health`
   xác nhận phiên bản, số nguồn và backend được dùng. Hỏi “PDF Bộ Y tế võng mạc”
   để kiểm tra bài `P01`, trang 9 và dòng `Neo4j / Cypher` trong trace.

```bash
python scripts/import_diabetes_neo4j.py --import --require-complete
```

Python xếp hạng ứng viên theo câu hỏi tiếng Việt. Neo4j trả nội dung, nguồn
và quan hệ đã lưu. Nếu phiên bản dữ liệu không khớp hoặc Neo4j mất kết nối,
chế độ `neo4j` báo lỗi tra cứu.

Trong **Aura Console → Query**, đối chiếu số URL và mở đồ thị bằng chứng PDF
của phiên bản đang dùng. Lấy giá trị `kb_version` từ đầu danh mục nguồn.

```cypher
MATCH (k:DiabetesKB {sources: 599}), (d:Document)-[:CITES]->(s:Source)
WHERE d.kb_version = k.version
RETURN k.version AS phien_ban, s.source_group AS nhom, s.source_type AS loai,
       count(DISTINCT s.source_id) AS so_nguon
ORDER BY phien_ban, nhom, loai;
```

```cypher
MATCH (k:DiabetesKB {sources: 599}),
      p=(a:Alias)-[:RETRIEVES]->(d:Document {id: 'P01'})-[:CITES]->(s:Source)
WHERE d.kb_version = k.version
RETURN p, d.page AS trang_pdf, d.section AS muc, s.source_url AS nguon
LIMIT 5;
```

Trên `/agents`, dùng các câu “Dinh dưỡng theo Bạch Mai nên chú ý gì?”,
“A1C cho biết điều gì trong kế hoạch chăm sóc?” và “PDF Bộ Y tế võng mạc” để
minh họa lần lượt bài web Việt Nam, bài web quốc tế và PDF.

## Triển khai

Website được triển khai trên **Render Free** bằng cấu hình [render.yaml](render.yaml).
Bản Render dùng CPU và mặc định dùng backend cục bộ. Để bật Aura, đặt các biến
Neo4j và `DIABETES_KB_BACKEND=neo4j` trong Environment của dịch vụ sau khi nhập
đúng phiên bản KB. Cấu hình Render tắt Gemini.
Service có thể cần thời gian khởi động sau khi ngủ; lịch sử chat trên ổ đĩa tạm
có thể mất sau khi khởi động lại.

Các kết quả dự đoán phục vụ học tập và nghiên cứu; phần tiểu đường không thay thế
chẩn đoán y tế.
