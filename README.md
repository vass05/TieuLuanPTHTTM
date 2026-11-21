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
trên máy phát triển. Tên file gồm tiền tố `VN` hoặc `QT`, tiêu đề và mã tài liệu.
Repository giữ PDF Bộ Y tế dùng cho demo, kèm dữ liệu
trích xuất và URL mở PDF gốc cho toàn bộ danh mục.

## Cấu trúc thư mục dự án

```text
TieuLuan/
├── app.py                            # Điểm khởi động Flask và đăng ký các trang/API
├── app_rag_api.py                    # API GraphRAG độc lập cho truy vấn y tế và tài chính
├── TieuLuan_HeThongThongMinh.ipynb    # Notebook huấn luyện và đánh giá các mô hình
├── .env.example                      # Mẫu biến Neo4j và Gemini cho môi trường cục bộ
├── requirements.txt                  # Thư viện chạy ứng dụng cục bộ
├── requirements-render.txt           # Thư viện cho bản chạy CPU trên Render
├── requirements-dev.txt              # Công cụ phát triển và kiểm thử
├── requirements-notebook-ch6.txt     # Thư viện chạy thí nghiệm chương 6
├── render.yaml                       # Lệnh build, khởi động và health check trên Render
├── gunicorn.conf.py                  # Cấu hình máy chủ WSGI
├── DATA/                             # Dữ liệu chạy mô hình và dùng trong notebook
│   ├── AMZN.csv                       # Chuỗi giá cổ phiếu Amazon
│   ├── AEP_hourly.csv                 # Phụ tải điện theo giờ
│   ├── vietnam_housing_dataset.csv    # Dữ liệu nhà đất Việt Nam
│   ├── pima_indians_diabetes.csv       # Dữ liệu dùng đánh giá MLP Pima
│   └── chapter6/                     # Tài liệu và câu hỏi dùng trong thí nghiệm truy xuất
├── knowledge/                        # Nội dung và nguồn phục vụ trợ lý tiểu đường
│   ├── diabetes_chat_documents.json   # Tóm tắt tiếng Việt cho tài liệu từ notebook
│   ├── diabetes_extended.json         # Bộ tài liệu mở rộng theo chủ đề
│   ├── diabetes_expansion.json        # Nguồn bổ sung và trích đoạn đã đối chiếu
│   ├── diabetes_editorial_overrides.json # Bản biên tập dùng khi tạo kho mở rộng
│   ├── diabetes_vietnam.json          # Bằng chứng từ nguồn Việt Nam ban đầu
│   ├── diabetes_sources.json          # Nguồn web bổ sung và bằng chứng PDF demo
│   ├── diabetes_pdf_sources.json      # Trích đoạn và số trang từ 199 PDF bổ sung
│   ├── DB_diabet.cypher               # Bản xuất Cypher để tạo kho trên Neo4j
│   └── sources/
│       ├── catalog.json              # Danh mục 599 nguồn, URL và vị trí trích dẫn
│       └── pdf/
│           ├── VN - Bộ Y tế 2558 - Võng mạc đái tháo đường [P01].pdf  # PDF demo trang 9
│           └── library/              # 199 PDF gốc giữ cục bộ để đối chiếu
├── model/                            # Trọng số và bộ tiền xử lý đã xuất
│   ├── amzn_lstm_model.keras          # Mô hình LSTM dùng để dự báo chuỗi
│   ├── best_housing_model.joblib      # Mô hình định giá nhà đã huấn luyện
│   ├── fashion_se_model.keras         # Mô hình SE-CNN nhận diện thời trang
│   ├── diabetes/                     # MLP Pima, bộ tiền xử lý và cấu hình dự đoán
│   ├── agents/                       # Chỉ mục, đồ thị, dữ liệu mẫu và Q-table chương 6
│   │   ├── manifest.json              # Phiên bản mô hình và mã kiểm tra artifact
│   │   ├── knowledge_documents.json  # Bộ tài liệu thực nghiệm đi cùng chỉ mục
│   │   ├── knowledge_index.joblib    # Chỉ mục TF-IDF/LSA đã xuất
│   │   ├── knowledge_graph.json      # Đồ thị nền dùng để nạp bộ truy xuất cục bộ
│   │   └── q_table.npy               # Bảng Q của chính sách điều phối thực nghiệm
│   └── vision/                       # Trọng số và thông tin mô hình CNN đọc chữ số
├── mvc/
│   ├── controllers/                  # Route Flask cho trợ lý, RAG, nhà đất, chuỗi thời gian và ảnh
│   │   ├── agents_controller.py      # Phiên chat, API hỏi đáp và API dự đoán tiểu đường
│   │   ├── housing_controller.py     # Trang và API định giá nhà
│   │   ├── timeseries_controller.py  # Trang và API dự báo chuỗi thời gian
│   │   ├── vision_controller.py      # Trang và API nhận diện thời trang, chữ số
│   │   └── rag_controller.py         # Trang và API truy xuất GraphRAG
│   ├── models/
│   │   ├── agents_model.py           # Điều phối truy xuất, dự đoán, kiểm chứng và ghi trace
│   │   ├── diabetes_dialogue.py      # Hiểu câu hỏi tiếng Việt và xếp hạng tài liệu
│   │   ├── neo4j_knowledge.py        # Chạy Cypher và đối chiếu bằng chứng trả về
│   │   ├── agent_store.py            # Lưu cuộc trò chuyện, tác vụ và trace vào SQLite
│   │   ├── chapter6_core.py          # MLP, truy xuất nền, kiểm chứng và chính sách điều phối
│   │   ├── prediction_dialogue.py    # Thu thập chỉ số và giải thích dự đoán
│   │   ├── assistant_synthesis.py    # Diễn đạt câu trả lời từ bằng chứng khi bật Gemini
│   │   ├── rag_model.py              # Bộ truy xuất riêng cho trang /rag và API độc lập
│   │   ├── housing_model.py          # Nạp mô hình và xử lý đặc trưng nhà đất
│   │   ├── timeseries_model.py       # Chuẩn hóa cửa sổ chuỗi và gọi mô hình dự báo
│   │   ├── vision_model.py           # Nhận diện ảnh thời trang
│   │   └── digit_model.py            # Tiền xử lý ảnh chữ số và suy luận CNN
│   ├── views/                        # Mẫu HTML, gồm agents.html cho trang /agents
│   └── static/
│       ├── css/                      # Bố cục và kiểu hiển thị
│       └── js/                       # agents.js xử lý chat, trích dẫn và trace trên giao diện
├── scripts/
│   ├── import_diabetes_neo4j.py       # Tạo bản xuất, danh mục và nhập kho vào Neo4j
│   ├── build_diabetes_knowledge.py    # Xuất đồ thị và số liệu cho phần báo cáo
│   ├── export_chapter6_project.py     # Đưa artifact từ kết quả notebook vào model/
│   ├── render-build.sh               # Cài thư viện và chạy bước kiểm tra build Render
│   └── check_render.py               # Kiểm tra các trang và mô hình của bản chạy CPU
├── tests/                            # Kiểm thử API, mô hình, hội thoại và truy xuất
│   └── test_neo4j_knowledge.py        # Kiểm thử số nguồn và bằng chứng PDF qua Neo4j
├── reports/
│   ├── chapter6/                     # Bảng, hình và số liệu thí nghiệm chương 6
│   └── project/                      # Ảnh và kết quả kiểm thử website để đối chiếu báo cáo
└── instance/                         # SQLite và dữ liệu chạy cục bộ do ứng dụng tạo
```

Đường dẫn `local_path` trong [danh mục nguồn](knowledge/sources/catalog.json)
tính từ `knowledge/`. Dùng `source_url` trong cùng bản ghi để mở tài liệu gốc.
Các thư mục `instance/` và `knowledge/sources/pdf/library/` được Git bỏ qua.

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

## Đọc mã trợ lý tiểu đường

1. [Controller Flask](mvc/controllers/agents_controller.py) nhận tin nhắn ở
   `/api/v1/assistant/chat`, kiểm tra phiên và chuyển yêu cầu cho model.
2. [AgentsModel](mvc/models/agents_model.py) điều phối truy xuất, kiểm chứng
   bằng chứng, trả lời và ghi trace. [DiabetesDialogue](mvc/models/diabetes_dialogue.py)
   chuẩn hóa câu hỏi tiếng Việt và xếp hạng các mã tài liệu ứng viên.
3. [Neo4jKnowledge](mvc/models/neo4j_knowledge.py) nhận các mã đã xếp hạng,
   chạy Cypher đọc tài liệu và đối chiếu nội dung, URL, trang PDF, quan hệ
   với kho cùng phiên bản. [Giao diện chat](mvc/static/js/agents.js) hiển thị
   bằng chứng và trace của từng tin nhắn.
4. [Trình xuất và nhập Neo4j](scripts/import_diabetes_neo4j.py) tạo
   `knowledge/DB_diabet.cypher` và danh mục từ cùng dữ liệu. Các cạnh
   `RETRIEVES` nối bí danh với tài liệu, `CITES` nối tài liệu với nguồn.
   Cạnh `FACT` nối hai khái niệm và lưu mã tài liệu trong `evidence_id`.

Các thư mục `__pycache__/`, `.pytest_cache/`, `pytest-cache-files-*/` và
`.ipynb_checkpoints/` do công cụ sinh. Tệp làm việc và kết quả chạy cục bộ
nằm trong `instance/`. Các ảnh và báo cáo kiểm thử trong `reports/project/`
phục vụ đối chiếu đồ án. Kho tri thức phục vụ trợ lý nằm trong `knowledge/`
và artifact của notebook trong `model/agents/`.

## Triển khai

Website được triển khai trên **Render Free** bằng cấu hình [render.yaml](render.yaml).
Bản Render dùng CPU và mặc định dùng backend cục bộ. Để bật Aura, đặt các biến
Neo4j và `DIABETES_KB_BACKEND=neo4j` trong Environment của dịch vụ sau khi nhập
đúng phiên bản KB. Cấu hình Render tắt Gemini.
Service có thể cần thời gian khởi động sau khi ngủ; lịch sử chat trên ổ đĩa tạm
có thể mất sau khi khởi động lại.

Các kết quả dự đoán phục vụ học tập và nghiên cứu; phần tiểu đường không thay thế
chẩn đoán y tế.
