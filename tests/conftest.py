import os
import pytest
import docx
import ebooklib
from ebooklib import epub
from reportlab.pdfgen import canvas

@pytest.fixture(scope="session", autouse=True)
def setup_test_fixtures():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # 1. TXT
    txt_path = os.path.join(fixtures_dir, "dummy.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Hello World TXT")
        
    # 2. DOCX
    docx_path = os.path.join(fixtures_dir, "dummy.docx")
    doc = docx.Document()
    doc.add_paragraph("Hello World DOCX")
    doc.save(docx_path)
    
    # 3. EPUB
    epub_path = os.path.join(fixtures_dir, "dummy.epub")
    book = epub.EpubBook()
    book.set_identifier("dummy_id_123")
    book.set_title("Dummy Title")
    book.set_language("vi")
    c1 = epub.EpubHtml(title="Chap 1", file_name="chap_1.xhtml", lang="vi")
    c1.content = "<html><body><p>Hello World EPUB</p></body></html>"
    book.add_item(c1)
    
    # Add navigation files to avoid error in ebooklib
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    book.spine = ['nav', c1]
    epub.write_epub(epub_path, book)
    
    # 4. PDF
    pdf_path = os.path.join(fixtures_dir, "dummy.pdf")
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "Hello World PDF")
    c.showPage()
    c.save()
    
    paths = {
        "txt": txt_path,
        "docx": docx_path,
        "epub": epub_path,
        "pdf": pdf_path
    }
    
    yield paths
    
    # Cleanup files after session
    for name, path in paths.items():
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
