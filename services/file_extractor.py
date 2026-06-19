import os
import docx
import pdfplumber
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings

# Tắt các cảnh báo không cần thiết từ EbookLib (như cảnh báo về chuẩn XML / Dublin Core)
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib")
warnings.filterwarnings("ignore", category=FutureWarning)

class FileExtractor:
    """
    Lớp tiện ích trích xuất nội dung văn bản thuần (plain text) từ các định dạng tệp khác nhau:
    - .docx (Microsoft Word)
    - .pdf (Portable Document Format)
    - .epub (Electronic Publication - Sách điện tử)
    - .txt (Tệp văn bản thuần)
    """

    def extract_docx(self, file_path: str) -> str:
        """
        Trích xuất văn bản từ tệp DOCX bằng thư viện python-docx.
        Đọc từng paragraph và nối lại bằng ký tự xuống dòng.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy tệp DOCX tại: {file_path}")
        
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n".join(paragraphs)

    def extract_pdf(self, file_path: str) -> str:
        """
        Trích xuất văn bản từ tệp PDF bằng thư viện pdfplumber.
        Giữ nguyên định dạng xuống dòng giữa các đoạn văn.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy tệp PDF tại: {file_path}")
        
        text_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
        
        # Nối các trang bằng hai ký tự xuống dòng để phân biệt trang
        return "\n\n".join(text_pages)

    def extract_epub(self, file_path: str) -> str:
        """
        Trích xuất văn bản từ tệp EPUB bằng ebooklib và BeautifulSoup4.
        Lọc qua các document item và loại bỏ các thẻ HTML để lấy văn bản sạch.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy tệp EPUB tại: {file_path}")
        
        book = epub.read_epub(file_path)
        text_parts = []
        
        for item in book.get_items():
            # Chỉ lấy các item thuộc kiểu tài liệu (ITEM_DOCUMENT)
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html_content = item.get_content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Trích xuất văn bản thuần và loại bỏ khoảng trắng thừa ở đầu/cuối
                text = soup.get_text()
                cleaned_text = text.strip()
                if cleaned_text:
                    text_parts.append(cleaned_text)
                    
        return "\n\n".join(text_parts)

    def extract_txt(self, file_path: str) -> str:
        """
        Đọc tệp văn bản thuần .txt với các bảng mã phổ biến (utf-8, utf-8-sig, latin-1).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy tệp TXT tại: {file_path}")
            
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'ansi', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # Nếu không tự động detect được bảng mã, đọc ở chế độ binary và bỏ qua lỗi giải mã
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def extract_text(self, file_path: str, extension: str) -> str:
        """
        Hàm chính tự động phát hiện định dạng tệp dựa trên extension
        và gọi phương thức xử lý tương ứng để trả về văn bản thuần.
        
        :param file_path: Đường dẫn tuyệt đối hoặc tương đối tới tệp cần trích xuất.
        :param extension: Đuôi tệp (ví dụ: '.docx', 'pdf', 'EPUB').
        :return: Chuỗi văn bản thuần của toàn bộ tệp.
        """
        # Chuẩn hóa phần mở rộng (ví dụ: ".docx", "pdf" -> "pdf" -> ".pdf")
        ext = extension.strip().lower()
        if not ext.startswith('.'):
            ext = '.' + ext
            
        if ext == '.docx':
            return self.extract_docx(file_path)
        elif ext == '.pdf':
            return self.extract_pdf(file_path)
        elif ext == '.epub':
            return self.extract_epub(file_path)
        elif ext == '.txt':
            return self.extract_txt(file_path)
        else:
            raise ValueError(f"Định dạng tệp không được hỗ trợ: {extension}. Chỉ hỗ trợ .docx, .pdf, .epub, .txt")

# Khởi tạo một instance mặc định để sử dụng nhanh
file_extractor = FileExtractor()
