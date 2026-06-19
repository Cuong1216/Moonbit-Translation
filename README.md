# Moonbit Translation

Hệ thống dịch thuật tiểu thuyết chuyên nghiệp và tự động trích xuất thuật ngữ (Glossary) cục bộ (Web App Local), được tối ưu hóa bằng Google Gemini API, Anthropic Claude, OpenRouter, và Ollama. Dự án được xây dựng với mục tiêu nâng cao độ chính xác, tính nhất quán của bản dịch tiểu thuyết dài tập (như tên nhân vật, địa danh, chiêu thức) thông qua việc áp dụng bảng thuật ngữ động.

---

## 1. Tổng quan & Cài đặt

### Tech Stack (Công nghệ sử dụng)
*   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) - Web framework hiệu năng cao cho Python.
*   **Web Server**: [Uvicorn](https://www.uvicorn.org/) - ASGI web server nhanh chóng.
*   **AI Integration**:
    *   `google-generativeai` (SDK chính thức của Google Gemini).
    *   `anthropic` (SDK chính thức của Anthropic Claude).
    *   `openai` (Được cấu hình để kết nối với API OpenRouter).
*   **File Parsers**:
    *   `python-docx`: Đọc và ghi tệp Microsoft Word (`.docx`).
    *   `pdfplumber`: Trích xuất nội dung văn bản chất lượng cao từ tệp `.pdf`.
    *   `EbookLib` & `beautifulsoup4`: Phân tích cấu trúc và lấy văn bản thuần từ sách điện tử `.epub`.
*   **Frontend**: HTML5, Vanilla CSS (Thiết kế Dark Mode hiện đại, Glassmorphic card, tùy chỉnh thanh cuộn), JavaScript (ES6, Server-Sent Events (SSE) để stream thời gian thực, quản lý trạng thái qua LocalStorage).

### Hướng dẫn cài đặt & Khởi chạy

#### Bước 1: Chuẩn bị môi trường Python
Yêu cầu Python từ phiên bản **3.9** trở lên. Mở Terminal tại thư mục gốc của dự án và chạy các lệnh sau để tạo và kích hoạt môi trường ảo:

*   **Trên Windows (PowerShell)**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
*   **Trên macOS/Linux**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

#### Bước 2: Cài đặt các thư viện phụ thuộc (Dependencies)
Cài đặt tất cả các gói thư viện cần thiết đã được định nghĩa trong tệp `requirements.txt`:
```bash
pip install -r requirements.txt
```

#### Bước 3: Cấu hình biến môi trường
1. Sao chép tệp cấu hình mẫu `.env.example` thành `.env`:
   *   **Windows (PowerShell)**: `copy .env.example .env`
   *   **Linux/macOS**: `cp .env.example .env`
2. Mở tệp `.env` vừa tạo và điền các khóa API của bạn vào:
   ```env
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   # Tùy chọn nếu sử dụng thêm các nhà cung cấp khác:
   ANTHROPIC_API_KEY=YOUR_CLAUDE_API_KEY_HERE
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
   ```

#### Bước 4: Khởi chạy Server
Để khởi động ứng dụng cục bộ, chạy lệnh trực tiếp thông qua Python:
```bash
python main.py
```
Hoặc chạy trực tiếp bằng lệnh `uvicorn`:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Sau khi khởi chạy thành công, truy cập giao diện web tại địa chỉ: [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 2. Hướng dẫn sử dụng (User Guide)

Hệ thống hoạt động theo quy trình khép kín nhằm đảm bảo chất lượng dịch thuật cao nhất. Dưới đây là giải thích chi tiết các tính năng và luồng thao tác chuẩn xác.

### Cấu hình API Key trên giao diện
*   Ở góc trên bên phải màn hình, chọn **Nhà cung cấp AI** ở Tab 2, sau đó nhập API Key tương ứng vào ô nhập liệu.
*   Hệ thống sẽ **tự động lưu trữ** mã khóa này vào LocalStorage của trình duyệt theo từng Provider (Gemini Key, Claude Key, OpenRouter Key) để bạn không cần nhập lại trong các lần sử dụng sau.
*   Có nút Ẩn/Hiện (biểu tượng con mắt) giúp bảo mật khóa API của bạn khi làm việc nơi công cộng.

### Tab 1: Quản lý Thuật ngữ (Glossary Builder)
Tính năng này giải quyết vấn đề lớn nhất của dịch thuật bằng AI: **sự không nhất quán**. (Ví dụ: Một nhân vật tên "Xiao Yan" chương trước được dịch là "Tiêu Viêm", chương sau lại bị dịch thành "Tiêu viêm" hoặc giữ nguyên tiếng Anh).

#### Tại sao cần chạy Tab quét Glossary trước?
Trước khi dịch một cuốn tiểu thuyết mới có các chương tiếp theo, bạn cần cung cấp cho AI một hoặc một vài chương **đã dịch chuẩn cũ** (bản gốc + bản dịch cũ tương ứng). Hệ thống sẽ đối chiếu song song từng câu/đoạn để nhận diện tên nhân vật, địa danh, chiêu thức, bảo vật và xuất ra bảng thuật ngữ thống nhất. Từ bảng này, khi dịch chương mới, AI bắt buộc phải tuân theo các quy tắc dịch thuật đã thiết lập.

#### Luồng thao tác quét thuật ngữ:
1.  Tại mục **Tự động quét thuật ngữ**:
    *   **Tệp tin raw cũ (Gốc)**: Tải lên chương truyện gốc chưa dịch (hỗ trợ `.docx`, `.pdf`, `.epub`, `.txt`).
    *   **Tệp tin đã dịch cũ (Đích)**: Tải lên chương tương ứng đã được dịch hoàn chỉnh bằng tiếng Việt.
2.  Nhấn nút **Tự động quét thuật ngữ**. Hệ thống sẽ chia nhỏ văn bản và gọi Gemini API chạy ngầm để phân tích.
3.  Sau khoảng 15-45 giây, kết quả sẽ hiển thị lên bảng **Danh sách thuật ngữ hiện tại**.
4.  **Tùy chỉnh thủ công**:
    *   **Sửa đổi**: Nhấp đúp chuột trực tiếp vào bất kỳ ô nào (Từ gốc hoặc Từ dịch) để sửa lại từ vựng cho đúng ý.
    *   **Thêm từ**: Nhấp vào nút **Thêm từ mới** ở đầu bảng để bổ sung thuật ngữ thủ công.
    *   **Xóa từ**: Nhấn vào biểu tượng thùng rác ở cuối mỗi dòng để xóa các từ rác hoặc dịch sai.
5.  **Lưu trữ**: Nhấn nút **Lưu bộ thuật ngữ** để lưu lại bảng này vào LocalStorage. Bảng này sẽ tự động được áp dụng làm tham chiếu đầu vào cho Tab dịch tiếp theo.

### Tab 2: Dịch Tiểu Thuyết Mới
Sau khi đã chuẩn bị xong bộ thuật ngữ ở Tab 1, chuyển qua Tab 2 để tiến hành dịch chương mới.

#### Luồng thao tác dịch thuật:
1.  **Tải tệp truyện**: Tải lên tệp tiểu thuyết mới cần dịch (raw). Hệ thống sẽ tự động trích xuất nội dung văn bản và hiển thị bản xem trước khoảng 1500 ký tự đầu tiên tại khung bên phải.
2.  **Cấu hình thông số**:
    *   Chọn **Ngôn ngữ gốc** (mặc định: Trung Quốc) và **Ngôn ngữ đích** (mặc định: Tiếng Việt).
    *   Chọn **Nhà cung cấp AI**: Google Gemini, Anthropic Claude, hoặc OpenRouter.
    *   Chọn **Model AI**: Ví dụ `Gemini 1.5 Flash` (Tốc độ cực nhanh, tiết kiệm chi phí) hoặc `Gemini 1.5 Pro` (Dịch mượt mà, văn phong văn học xuất sắc hơn).
    *   Kiểm tra số lượng thuật ngữ đang áp dụng hiển thị ở hộp thông tin trạng thái.
3.  **Bắt đầu dịch**: Nhấn nút **Bắt đầu dịch thuật**.
4.  **Theo dõi tiến trình**:
    *   Thanh **Progress Bar** và số phần trăm (%) sẽ liên tục cập nhật tiến độ dịch thời gian thực.
    *   Khung **Xem trước bản dịch** sẽ hiển thị nội dung được dịch tuần tự theo từng đoạn nhờ cơ chế **Server-Sent Events (SSE)**. Bạn có thể đọc trực tiếp bản dịch ngay khi hệ thống đang xử lý các đoạn sau.
5.  **Tính năng Tạm dừng & Tiếp tục (Pause & Resume)**:
    *   Nếu có việc bận hoặc muốn dừng lại để kiểm tra, nhấn nút **Tạm dừng**. Hệ thống sẽ hoàn thành nốt đoạn đang dịch dở và tạm dừng tiến trình một cách an toàn.
    *   Trạng thái dịch (bao gồm vị trí đoạn hiện tại, danh sách các đoạn đã dịch xong) sẽ được tự động ghi xuống file cục bộ `translation_state.json` trên máy chủ.
    *   Khi bạn muốn dịch tiếp, chỉ cần nhấn nút **Tiếp tục**. Giao diện sẽ tiếp tục kết nối đến endpoint SSE và dịch tiếp từ đoạn bị tạm dừng mà không phải dịch lại từ đầu, giúp tiết kiệm tối đa token API.
6.  **Tải file kết quả**:
    *   Khi thanh tiến trình đạt **100%**, hộp thoại thông báo hoàn thành xuất hiện.
    *   Nút **Tải file kết quả** sẽ hiển thị. Bạn có thể chọn tải về dưới dạng tệp văn bản thuần `.txt` hoặc tệp Word `.docx` được định dạng xuống dòng chuẩn xác.

---

## 3. Đánh giá Code & Đề xuất Hướng phát triển (Roadmap)

Dưới góc nhìn của một Lead Architect, dưới đây là đánh giá kỹ thuật khách quan về cấu trúc mã nguồn hiện tại cùng lộ trình nâng cấp hệ thống.

### Đánh giá Kiến trúc Hiện tại

#### Điểm mạnh (Strengths)
1.  **Thiết kế lỏng lẻo & Dễ mở rộng (Extensible Design)**: Sử dụng **Strategy Pattern** và **Factory Pattern** cho các dịch vụ dịch thuật (`translator.py`). Việc thêm các nhà cung cấp dịch thuật mới (như OpenAI, Cohere, v.v.) chỉ đơn giản là kế thừa từ `BaseTranslator` và đăng ký trong `TranslatorFactory` mà không làm ảnh hưởng đến mã nguồn hiện tại.
2.  **Xử lý văn bản thông minh (Smart Chunking)**: Hàm `smart_chunking` trong `NovelTranslator` hoạt động xuất sắc. Thay vì cắt văn bản thô thiển theo độ dài ký tự cố định làm đứt câu giữa chừng, thuật toán ưu tiên cắt theo đoạn văn (`\n`), và tự động phân tách theo các dấu câu cuối câu (`.!?`) đối với các đoạn quá dài. Điều này đảm bảo ngữ cảnh của câu dịch được toàn vẹn.
3.  **Khả năng phục hồi lỗi & Tối ưu hóa API**:
    *   Cơ chế **Retry logic** thông minh (thử lại tối đa 3 lần, nghỉ 5 giây) giúp hệ thống vượt qua các lỗi tạm thời của API như quá tải tài nguyên (`ResourceExhausted`) hoặc lỗi dịch vụ (`ServiceUnavailable`).
    *   Hàm `resolve_model_name` tự động phát hiện model khả dụng trên API key và tự động fallback sang model Flash hoặc model khả dụng khác. Điều này giúp ngăn chặn triệt để lỗi `404 Model Not Found`.
4.  **Kiểm soát tiến trình tốt**: Kết hợp giữa **Server-Sent Events (SSE)** ở Frontend và lưu trữ trạng thái dịch cục bộ vào tệp `translation_state.json` giúp hệ thống có khả năng Pause/Resume bền bỉ, không bị mất dữ liệu khi gián đoạn kết nối mạng.

#### Điểm yếu (Weaknesses)
1.  **Trạng thái dịch đơn luồng (Single Session Limit)**: Biến `active_task` được khai báo dưới dạng biến toàn cục trong `api/routes.py`. Thiết kế này chỉ hỗ trợ duy nhất một tiến trình dịch chạy tại một thời điểm trên toàn server. Nếu có hai tab trình duyệt cùng lúc thực hiện yêu cầu dịch, dữ liệu của phiên dịch trước sẽ bị ghi đè hoàn toàn.
2.  **Thiếu cơ sở dữ liệu thực thụ (No Database)**: Việc lưu trữ Glossary hoàn toàn dựa vào LocalStorage của trình duyệt khiến người dùng gặp khó khăn khi muốn chuyển đổi giữa các thiết bị hoặc muốn quản lý nhiều bộ từ vựng cho nhiều bộ tiểu thuyết khác nhau.
3.  **Nguy cơ nghẽn I/O khi lưu trạng thái**: Hàm `save_active_task_state()` ghi file `translation_state.json` một cách đồng bộ (`open()`) sau mỗi chunk dịch xong. Đối với các file tiểu thuyết lớn chia thành hàng trăm chunk, việc ghi file đồng bộ liên tục có thể gây suy giảm hiệu năng I/O của đĩa cứng.

### Đề xuất Hướng phát triển (Roadmap nâng cấp)

Dưới đây là các tính năng được đề xuất nâng cấp nhằm tối ưu hiệu năng backend và mang lại trải nghiệm người dùng premium, sắp xếp theo thứ tự ưu tiên từ cao xuống thấp:

*   **Tích hợp Trình biên tập song song (Split-screen Editor - Ưu tiên Cao nhất)**: Giao diện chia đôi màn hình: bên trái hiển thị đoạn văn gốc (Source Paragraph), bên phải hiển thị đoạn văn dịch tương ứng (Target Paragraph), cho phép người dùng đối chiếu trực tiếp từng đoạn và sửa trực tiếp bản dịch bị lỗi từ AI ngay trên màn hình trước khi nhấn nút xuất file Word/Text cuối cùng.
*   **Chuyển đổi sang SQLite để quản lý đa Glossary (Ưu tiên Cao)**: Thay thế lưu trữ LocalStorage bằng một cơ sở dữ liệu SQLite cục bộ siêu nhẹ tích hợp sẵn trong ứng dụng FastAPI. Cho phép người dùng tạo và đặt tên cho nhiều bộ thuật ngữ khác nhau, dễ dàng backup, import/export tệp tin thuật ngữ định dạng `.csv` hoặc `.json`.
*   **Tái cấu trúc Backend hỗ trợ Đa tiến trình dịch song song (Ưu tiên Trung bình)**: Chuyển đổi cơ chế lưu `active_task` toàn cục thành kiến trúc Session-based hoặc sử dụng hàng đợi công việc nền (chẳng hạn như `BackgroundTasks` của FastAPI gắn với `session_id`, hoặc kết hợp Celery + Redis/SQLite cho hệ thống lớn). Cho phép chạy đồng thời nhiều tiến trình dịch khác nhau mà không bị tranh chấp tài nguyên.
*   **Tích hợp Bộ nhớ dịch thuật (Translation Memory - TM - Ưu tiên Thấp)**: Xây dựng một cơ chế lưu lại các phân đoạn câu đã dịch thành công (Sentence pairs) vào database để thực hiện đối chiếu độ tương đồng (Fuzzy Matching) cho các câu trùng lặp hoặc tương đồng cao, giúp lấy trực tiếp kết quả cũ, tiết kiệm đáng kể chi phí token API và tăng tốc độ dịch tổng thể lên tới 15-20%.
