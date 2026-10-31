# Trợ lý tiểu đường

Chatbot hỗ trợ hỏi đáp về tiểu đường và tra cứu tài liệu có nguồn. Giao diện có
hai cột: **bên trái là cuộc trò chuyện**, **bên phải là luồng điều phối AI**,
dùng cùng màu xanh dương, nền và kiểu thẻ của các trang còn lại. Người dùng chỉ
nhập tin nhắn; không có biểu mẫu chỉ số hoặc nút chọn chế độ xử lý.
Backend tự nhận diện chủ đề, chọn truy xuất và kiểm chứng nguồn. Các API mô hình
nghiên cứu và đối chứng vẫn được giữ riêng. Trang chủ chuyển đến `/agents`.
Kéo thanh giữa hai khung để đổi độ rộng (30–70%); có thể dùng phím mũi tên,
Home/End khi thanh được chọn. Tỉ lệ được lưu trên trình duyệt; nhấp đúp để đặt lại.
Trên điện thoại, chatbot nằm trên và phần điều phối nằm dưới.

## Chạy ứng dụng

Tại thư mục project, trong môi trường Python đã cài các thư viện:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Mở **http://127.0.0.1:5000/agents**. Nếu đã cài đủ thư viện trong môi trường hiện tại,
chỉ cần lệnh thứ hai. Phần mới đã được kiểm tra với Python 3.14, NumPy 2.5.1,
Scikit-learn 1.9.0 và PyTorch CPU 2.14.1. Scikit-learn được cố định theo phiên bản
đã xuất artifact; requirements mới yêu cầu Python từ 3.11. Không cần API key,
TensorFlow hoặc dịch vụ đồ thị để chạy phần trả lời từ kho cục bộ.

API tổng hợp được cấu hình **chỉ ở server**, không có ô nhập khóa trên giao diện.
Ứng dụng tự đọc `GEMINI_API_KEY` từ môi trường hoặc `.env` hiện có như trang RAG.
Xem mẫu `.env.example`; không đưa khóa thật vào Git. Cấu hình tùy chọn:

```dotenv
GEMINI_API_KEY=<khóa của bạn>
ASSISTANT_EXTERNAL_ENABLED=true
ASSISTANT_GEMINI_MODEL=gemini-3.5-flash-lite
```

Khởi động lại server sau khi đổi cấu hình. Khi có bằng chứng, API nhận câu hỏi và
các tóm tắt công khai để diễn đạt câu trả lời. Không gửi hồ sơ Pima, cookie,
mã phiên hoặc toàn bộ lịch sử. Mỗi đoạn phải có ID nguồn và trích đoạn hỗ trợ
khớp tài liệu. Thiếu khóa, timeout, hết hạn mức hoặc đầu ra không hợp lệ sẽ dùng
phản hồi từ kho cục bộ; có thời gian nghỉ 60 giây sau lỗi API. Không có nguồn thì
không yêu cầu mô hình tự bịa câu trả lời. Kiểm tra trích dẫn là kiểm tra cấu trúc,
chưa chứng minh mọi phát biểu sinh ra đều đúng về y khoa.

Các artifact đã được đặt ở `model/diabetes/` và `model/agents/`; ứng dụng chỉ nạp
để suy luận, không tự huấn luyện. Nếu vừa chạy lại notebook hoặc cần đóng gói lại:

```powershell
python scripts/export_chapter6_project.py
```

Script kiểm tra checksum artifact nguồn, tạo mã suy luận từ các định nghĩa trong
notebook, sửa tham chiếu hàm chuẩn hóa để pickle có thể nạp ngoài kernel, và xuất
manifest của bản đóng gói. Không sửa notebook hay chạy huấn luyện. Sau khi export,
khởi động lại ứng dụng để nạp bản mới.

## Những luồng có thể demo

1. Gửi **Xin chào**. Phần điều phối ghi nhận lời chào và trả lời giao tiếp,
   không giả lập việc gọi RAG hay mô hình dự đoán.
2. Gửi **Tiểu đường ăn được gì**. Quan sát nhánh RAG/đồ thị được tô xanh bên phải,
   kế hoạch, tài liệu NIDDK và các sự kiện kiểm chứng thực tế.
3. Hỏi tiếp **Còn những loại nào nữa?**. Backend dùng chủ đề từ cuộc trò chuyện;
   tin nhắn mới và trả lời được thêm vào khung chat, có nhãn sử dụng ngữ cảnh.
4. Hỏi **Hoạt động thể chất có vai trò gì?** để chuyển chủ đề, hoặc **Liệu có bị
   tiểu đường** để tra cứu thông tin xét nghiệm. Không cần nhập bảng chỉ số.
5. Hỏi một câu ngoài miền như quỹ đạo sao Hỏa. Hệ thống thông báo thiếu bằng chứng,
   không dùng ngữ cảnh dinh dưỡng để trả lời một câu không liên quan.
6. Bấm **Xem luồng xử lý** dưới một phản hồi cũ để xem lại đúng kế hoạch và trace
   của tin nhắn đó. Các mô hình không được gọi vẫn hiển thị trạng thái chưa cần.
7. Tải lại trang hoặc chọn lịch sử để mở lại cuộc trò chuyện. **Cuộc trò chuyện mới**
   bắt đầu luồng mới; nút xóa lịch sử chỉ xóa các cuộc trò chuyện của phiên hiện tại.
8. Thử **Tiểu đường uống rưởu được không?**, **Tiểu đường tuýp 2 là gì?**,
   **tiểu đường uống nước cam được khônh**. Kiểm tra nguồn theo đúng chủ đề.
9. Gửi **Tôi muốn đánh giá nguy cơ tiểu đường bằng các chỉ số sức khỏe** hoặc bấm
   **Đánh giá bằng chỉ số**. Chatbot hỏi dữ liệu còn thiếu trong cuộc trò chuyện.
   Khi đủ chỉ số, đúng đơn vị và phạm vi, backend gọi MLP thật; nhánh dự đoán sáng lên.
10. Bấm **Thử dữ liệu mẫu** hoặc gửi **Chạy thử dự đoán bằng dữ liệu mẫu** để xem
    ngay một lượt suy luận. Kết quả được ghi rõ là mẫu nghiên cứu và lưu cùng lịch sử.

Nhánh dự đoán cần tuổi, số lần mang thai, glucose sau 2 giờ OGTT (mg/dL), huyết áp
tâm trương (mmHg), độ dày nếp gấp da (mm), insulin huyết thanh sau 2 giờ (µU/mL),
BMI và chỉ số phả hệ DPF. Cần xác nhận hồ sơ thuộc phụ nữ từ 21 tuổi; hồ sơ không
phù hợp sẽ không được chấm điểm. Glucose lúc đói không thay thế glucose OGTT.
Không tự điền chỉ số thiếu hoặc đổi sang dữ liệu mẫu nếu người dùng chưa yêu cầu.
DPF không phải một câu trả lời có/không về tiền sử gia đình.
Có thể dán hồ sơ có nhãn trực tiếp vào chat, kể cả sau khi thử dữ liệu mẫu.
Nhãn đầy đủ như `Chỉ số phả hệ tiểu đường (DPF): 1.080` được đọc là DPF=1.08;
ngoặc chứa tên viết tắt và dấu phẩy thập phân cũng được hỗ trợ. Hồ sơ mới sau
lượt demo không kế thừa các chỉ số của mẫu.
Kết quả mở đầu bằng nhóm mô hình phân loại: “có tiểu đường” (nhãn 1) hoặc
“không tiểu đường” (nhãn 0), kèm giới hạn của kết quả nghiên cứu. Sau đó có thể hỏi
**Vậy tôi có bị tiểu đường không?** hoặc **Kết quả này là sao?** để giải thích kết quả
đã lưu trong cùng cuộc trò chuyện; không nhập lại hồ sơ và không chạy lại mô hình.
Kết quả dữ liệu mẫu luôn được phân biệt với hồ sơ cá nhân, kể cả khi hỏi tiếp.
Giao diện hiển thị nhóm phân loại bằng tiêu đề nổi bật từ nhãn mô hình đã lưu,
kể cả khi mở lại câu trả lời cũ chỉ ghi “nhãn nghiên cứu: 0/1”.

Bạn có thể gửi nhiều chỉ số trong một tin nhắn có nhãn, ví dụ `Tôi là nữ, 47 tuổi;
BMI=35,5`. Đơn vị không khớp phải được làm rõ. Gõ **Hủy dự đoán** để dừng thu thập,
hoặc hỏi một chủ đề kiến thức để chuyển sang hỏi đáp. Điểm trả về là điểm phân loại
nghiên cứu trên thang 0–1, không phải xác suất chẩn đoán cá nhân.

Ở các API nghiên cứu, Q-learning dùng Q-table cố định từ seed 11 của notebook, với 32 trạng thái và năm
hành động cho nhiệm vụ dự đoán kèm bằng chứng. Rule-Based là mặc định. Mỗi lần
thực thi có giới hạn mười bước, sáu lượt gọi công cụ và deadline kiểm tra giữa các
lời gọi đồng bộ. Không học online từ dữ liệu người sử dụng. Độ trễ của một cặp
so sánh không đủ để suy ra chính sách nào tốt hơn.

## API

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| GET | `/api/v1/health` | Trạng thái mô hình và khả năng phục vụ |
| POST | `/api/v1/assistant/chat` | Gửi `message`, tùy chọn `conversation_id`; server tự lập kế hoạch |
| GET | `/api/v1/assistant/conversations` | Danh sách cuộc trò chuyện của phiên |
| GET | `/api/v1/assistant/conversations/<id>` | Mở lại tin nhắn và trace của một cuộc trò chuyện |
| DELETE | `/api/v1/assistant/conversations` | Xóa lịch sử chat của phiên, giữ các tác vụ nghiên cứu cũ |
| GET | `/api/v1/agents/session` | Cấu hình giao diện, mẫu nghiên cứu và CSRF token |
| POST | `/api/v1/predict` | Dự đoán Pima từ `profile`, có kiểm tra đầu vào |
| POST | `/api/v1/knowledge/search` | Truy xuất theo `query`, `top_k`, `method` |
| POST | `/api/v1/safety/validate` | Kiểm tra `profile`, `query`, `mode`, `units` |
| POST | `/api/v1/agents/execute` | Điều phối tác vụ mới hoặc bổ sung theo `task_id` |
| POST | `/api/v1/agents/compare` | Thực thi cùng dữ liệu với hai chính sách |
| GET | `/api/v1/agents/status/<task_id>` | Xem trạng thái, kết quả và trace trong phiên |
| GET | `/api/v1/agents/history` | Lịch sử của phiên, `limit` từ 1 đến 50 |
| DELETE | `/api/v1/agents/history` | Xóa lịch sử phiên hiện tại |

API ghi dữ liệu yêu cầu `Content-Type: application/json` (trừ DELETE không có body)
và header `X-CSRF-Token` nhận từ `/api/v1/agents/session`. Giữ cookie giữa các
request. Ví dụ bằng Python:

```python
import requests

client = requests.Session()
base = "http://127.0.0.1:5000"
setup = client.get(base + "/api/v1/agents/session").json()
headers = {"X-CSRF-Token": setup["csrf_token"]}
result = client.post(base + "/api/v1/assistant/chat", headers=headers, json={
    "message": "Tiểu đường ăn được gì",
}).json()
print(result["task"]["outcome"])
# Gửi câu tiếp theo với result["conversation_id"] để giữ ngữ cảnh.
```

Các API nghiên cứu giữ hai chế độ `predict_explain`, `knowledge` và hai chính sách
`rule`, `q_learning` để tái lập thực nghiệm; giao diện chat không yêu cầu lựa chọn chúng.
Để tiếp tục tác vụ đang `REQUEST_INFO` hoặc `NO_EVIDENCE`, gửi `task_id` và dữ liệu
bổ sung bằng cùng cookie. Tác vụ đã kết thúc không được mở lại. Các trạng thái
nghiệp vụ nằm trong `task.outcome`: `ANSWERED`, `REQUEST_INFO`, `NO_EVIDENCE`,
`ESCALATE`, `OUT_OF_SCOPE`, `TOOL_OR_BUDGET_ERROR`. HTTP 200 nghĩa là yêu cầu đã được xử lý để trả
trạng thái; không đồng nghĩa đã có câu trả lời. Lỗi schema là 400, phiên không
hợp lệ là 403, tác vụ không thuộc phiên là 404, xung đột là 409, thiếu mô hình là
503. Thiếu dữ liệu không được bù bằng kết quả dự đoán ngẫu nhiên.

## Bộ nhớ và phạm vi dữ liệu

`instance/agents.sqlite3` lưu tin nhắn, ID cuộc trò chuyện, kế hoạch, kết quả và trace.
Ngữ cảnh chỉ được dùng cho câu hỏi tiếp nối có dấu hiệu liên quan; một câu hỏi độc
lập không tự nhận chủ đề từ tin trước. Các API nghiên cứu cũ có thể lưu hồ sơ để
tiếp tục tác vụ. Phần chat thu thập chỉ số trong tin nhắn chỉ khi người dùng yêu cầu
dự đoán; trạng thái thu thập được lưu riêng theo cuộc trò chuyện, không đưa vào trace
hoặc gửi sang API tổng hợp. Các câu hỏi kiến thức không cần cung cấp chỉ số.
Trace không chứa toàn bộ hồ sơ. `instance/session_secret.key` là khóa ký phiên
cục bộ để cookie vẫn dùng được sau khi khởi động lại. Toàn bộ `instance/` được
loại khỏi Git. Có thể dùng biến môi trường `FLASK_SECRET_KEY` để tự quản lý khóa.
Nếu thay khóa hoặc xóa cookie, phiên cũ không còn được mở từ trình duyệt đó.

Đây là bản demo nghiên cứu cục bộ, chưa có tài khoản nhân viên y tế, phân quyền
cơ sở khám chữa bệnh hay quy trình triển khai dữ liệu bệnh nhân thật. Pima là
đoàn hệ lịch sử phụ nữ từ 21 tuổi. Glucose là chỉ số sau hai giờ OGTT, không phải
glucose lúc đói. Điểm mô hình và nhãn nghiên cứu không được diễn giải thành
chẩn đoán cá nhân.

Kho hội thoại gồm **168 tài liệu từ 163 trang nguồn**, gấp bốn số tài liệu ban đầu:
NIDDK/NIH, CDC, MedlinePlus, ADA, NHS, Diabetes UK và Public Health Agency of Canada.
Đồ thị có **593 thực thể, 410 quan hệ chuyên môn có nguồn**. Tổng 1736 nút và 1418 cạnh
còn có tài liệu, trang nguồn và 812 bí danh truy xuất; bí danh không được tính là thực thể y khoa. Các số này là
kích thước dữ liệu, không phải điểm đánh giá chất lượng tư vấn.

Lớp hội thoại của project nhận diện cách hỏi thông thường như “tiểu đường ăn được
gì”, “nên ăn gì”, “kiêng ăn gì”, kể cả khi không gõ dấu, rồi mở rộng truy vấn sang
từ vựng của chủ đề trước khi truy xuất. Ngưỡng lọc bằng chứng vẫn được giữ; không
trả lời bằng một tài liệu giả nếu truy xuất thất bại. Phần bổ sung nội dung đã
đối chiếu nguồn nằm ở `knowledge/diabetes_chat_documents.json` và `knowledge/diabetes_extended.json`.
Phần mở rộng thêm 126 trang nguồn riêng biệt nằm ở `knowledge/diabetes_expansion.json`;
các chỉnh sửa nội dung và bộ ba đồ thị nằm ở `knowledge/diabetes_editorial_overrides.json`.
Mỗi tài liệu mới có URL, ngày truy cập, hash trang gốc và trích đoạn hỗ trợ. Bản thảo
được hỗ trợ bằng API, qua lượt đối chiếu riêng với nguồn rồi biên tập các điểm cần sửa;
quy trình này chưa thay thế thẩm định lâm sàng. Chi tiết ở `reports/project/corpus_source_review.json`.
Script `scripts/expand_diabetes_corpus.py` chỉ chạy khi xây dựng kho, không tự duyệt web
trong mỗi lượt chat. Trang thô và phản hồi bản thảo nằm trong thư mục checkpoint được Git bỏ qua.
Các nhóm bổ sung gồm tuýp 1/2, tiền tiểu đường, thai kỳ, rượu bia, nước ép,
thực phẩm, thuốc, biến chứng mắt/thận/thần kinh/tim, bàn chân, răng miệng, CGM,
ngày ốm, đi xa, giấc ngủ, tinh thần và các hiểu lầm thường gặp.
Truy xuất dùng bí danh trên đồ thị, TF-IDF từ và n-gram ký tự để hỗ trợ cách gõ
không dấu và một số lỗi chính tả; chưa có transformer embedding hoặc Neo4j.
Xuất đồ thị bằng `python scripts/build_diabetes_knowledge.py`;
kết quả tại `reports/project/knowledge_graph.json` và `knowledge_summary.json`.

Chỉ mục thực nghiệm được giữ nguyên để đối chiếu notebook. Lớp mở rộng truy vấn
và nội dung phục vụ hội thoại là phần cải tiến riêng của project, cần đánh giá
riêng; không dùng kết quả benchmark cũ như số đo chất lượng của lớp mới.
Trợ lý dùng nội dung có nguồn và có thể nhờ API diễn đạt lại trong phạm vi đó.
Kho hiện tại vẫn có giới hạn; không bảo đảm trả lời mọi câu hỏi y khoa.
Q-learning chỉ lựa chọn bước gọi công cụ trong nhánh phân
tích chỉ số, không học ngôn ngữ hay tự tạo kiến thức y khoa.

Các trang cũ `/housing`, `/vision`, `/timeseries`, `/rag` và API cũ được giữ lại.
Trang `/timeseries` nạp trực tiếp `model/amzn_lstm_model.keras` và
`model/time_series_scaler.pkl`. Keras tự chọn PyTorch nếu không có TensorFlow;
`requirements.txt` đã bao gồm Keras và h5py. Không huấn luyện lại hoặc đổi trọng số.
Nguồn mặc định lấy **giá đóng cửa AMZN của phiên hoàn tất gần nhất từ Yahoo Finance**,
qua [yfinance](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html),
không cần API key. Đây là dữ liệu theo phiên, có thể trễ từ nhà cung cấp, không phải giá khớp lệnh trực tiếp.
Server giữ bộ nhớ đệm tối đa 5 phút; giao diện ghi nguồn, ngày phiên và thời điểm lấy dữ liệu.
Chỉ dùng phiên đã đóng cửa theo lịch sàn, dự báo bỏ cuối tuần và ngày nghỉ giao dịch.
Không lấy được đúng phiên gần nhất thì trang/API trả 503 và cho phép chọn CSV rõ ràng;
không thay ngầm bằng CSV năm 2023. `source=dataset` của client cũ cũng chuyển sang nguồn trực tuyến.
Chọn `source=amzn_csv` để đối chiếu dữ liệu lịch sử; `source=aep_csv&symbol=AEP`
là bộ phụ tải điện ngoại tuyến, không phải giá cổ phiếu AEP trực tuyến.
Nếu đã mở server trước khi cập nhật, dừng server và chạy lại `python app.py` sau khi
cài `python -m pip install -r requirements.txt`. Backend cấu hình rõ qua
`KERAS_BACKEND` sẽ được giữ nguyên. Chi tiết: [cấu hình backend Keras](https://keras.io/getting_started/).
Trang `/vision` cũng dùng bộ nạp Keras chung để chạy trực tiếp
`model/fashion_se_model.keras` bằng PyTorch khi không có TensorFlow. Cả nét vẽ
base64 và ảnh tải lên đều được đưa về ảnh xám 28×28; PNG trong suốt được ghép nền trắng.
Trọng số SE-CNN giữ nguyên, không huấn luyện lại. Ảnh không đọc được trả JSON 400;
lỗi mô hình trả 503 với thông báo cụ thể trên giao diện, không bật hộp thoại chỉ ghi mã lỗi.
Trên trang thị giác, chọn **Chữ số viết tay (0–9)** tại **Bạn muốn nhận diện** để
vẽ một chữ số hoặc tải ảnh chữ số lên. Chế độ này gọi CNN MNIST riêng; chế độ
**Sản phẩm thời trang** tiếp tục dùng SE-CNN Fashion-MNIST. Chuyển chế độ sẽ xóa
kết quả đang hiển thị và giữ ảnh/nét vẽ để bạn nhận diện lại.
CNN chữ số đạt **99,03% trên 10.000 ảnh kiểm tra MNIST chính thức**, sau khi chọn
checkpoint bằng tập validation 6.000 ảnh; tập train có 54.000 ảnh. Đây là số đo trên
bộ kiểm tra MNIST. Mô hình, checksum và cấu hình nằm trong `model/vision/`;
log huấn luyện và ma trận nhầm lẫn ở `reports/project/mnist_training.json`.
Web chỉ nạp trọng số đã lưu; ảnh được xử lý cục bộ. Bảng trống được báo cần vẽ chữ.

Có thể huấn luyện lại bằng `python scripts/train_digit_model.py` khi có
`DATA/mnist_train.csv` gồm 60.000 hàng và 785 cột (nhãn ở cột đầu).
Script tách train/validation theo seed 42, dùng cùng tiền xử lý với web, và tải
bộ kiểm tra MNIST chính thức từ mirror được [Torchvision sử dụng](https://github.com/pytorch/vision/blob/main/torchvision/datasets/mnist.py).
CSV lớn và cache dữ liệu không được đưa lên GitHub; trọng số nhỏ đã được kèm trong project.

Khi thiếu thành phần, API trả 503/trang thông báo phù hợp, thay
cho xác suất ngẫu nhiên hay dự báo giả lập. Hai bộ artifact cũ của XGBoost và
MinMaxScaler được tạo bằng phiên bản thư viện khác nên vẫn có cảnh báo tương
thích lúc nạp; chúng không tham gia luồng trợ lý tiểu đường.

## Kiểm tra

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_agents_project.py tests/test_diabetes_extension.py tests/test_prediction_chat.py tests/test_corpus_expansion.py tests/test_timeseries_runtime.py tests/test_market_data.py tests/test_vision_runtime.py tests/test_digit_model.py -q
node --check mvc/static/js/agents.js
```

Kiểm tra giao diện bằng Chrome/Edge headless trên Windows (khởi động ứng dụng ở
cổng 5000 trước):

```powershell
python scripts/check_agents_browser.py
python scripts/check_timeseries_browser.py
python scripts/check_vision_browser.py
```

Script dùng profile trình duyệt tạm riêng trong `.ipynb_checkpoints/`, chỉ thao
tác dữ liệu mẫu và xóa lịch sử của phiên kiểm thử khi hoàn tất.
Kiểm thử backend tự tắt API thật và giả lập timeout, hết hạn mức, JSON lỗi và
trích dẫn sai. Kiểm tra trình duyệt chuẩn chạy với `ASSISTANT_EXTERNAL_ENABLED=false`
để đối chiếu nội dung cục bộ ổn định; API thật được kiểm tra riêng bằng câu hỏi mẫu.

Kiểm thử đối chiếu điểm MLP với trace notebook, đối chiếu truy xuất với toàn bộ
72 cặp phương pháp/câu hỏi đã lưu, kiểm tra bổ sung dữ liệu, lỗi công cụ, bằng
chứng bị sửa, Q-table bất biến, lịch sử bền vững và tách biệt phiên.

Kết quả kiểm tra trình duyệt và ảnh demo nằm trong `reports/project/`.
Ghi chú mục/trang và chú thích ảnh để chèn phần project vào v3:
`reports/project/HUONG_DAN_CHEN_PROJECT.md`.
Hướng dẫn chèn kết quả notebook vào tài liệu vẫn ở
`reports/chapter6/HUONG_DAN_CHEN_CHUONG6.md`.
