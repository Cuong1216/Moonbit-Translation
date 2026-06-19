import os
import pytest
from services.file_extractor import file_extractor

@pytest.mark.asyncio
async def test_extract_txt(setup_test_fixtures):
    txt_path = setup_test_fixtures["txt"]
    content = await file_extractor.extract_txt(txt_path)
    assert isinstance(content, str)
    assert "Hello World TXT" in content

@pytest.mark.asyncio
async def test_extract_docx(setup_test_fixtures):
    docx_path = setup_test_fixtures["docx"]
    content = await file_extractor.extract_docx(docx_path)
    assert isinstance(content, str)
    assert "Hello World DOCX" in content

@pytest.mark.asyncio
async def test_extract_epub(setup_test_fixtures):
    epub_path = setup_test_fixtures["epub"]
    content = await file_extractor.extract_epub(epub_path)
    assert isinstance(content, str)
    assert "Hello World EPUB" in content

@pytest.mark.asyncio
async def test_extract_pdf(setup_test_fixtures):
    pdf_path = setup_test_fixtures["pdf"]
    content = await file_extractor.extract_pdf(pdf_path)
    assert isinstance(content, str)
    assert "Hello World PDF" in content

@pytest.mark.asyncio
async def test_extract_text_dispatcher(setup_test_fixtures):
    for ext, path in setup_test_fixtures.items():
        content = await file_extractor.extract_text(path, ext)
        assert isinstance(content, str)
        assert f"Hello World {ext.upper()}" in content

@pytest.mark.asyncio
async def test_extract_unsupported_format():
    with pytest.raises(ValueError, match="Định dạng tệp không được hỗ trợ"):
        await file_extractor.extract_text("dummy.xyz", ".xyz")
