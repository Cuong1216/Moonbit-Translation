import pytest
import hashlib
from unittest.mock import MagicMock, patch
from services.translator import GeminiTranslator
from database import SessionLocal, TranslationMemory

@pytest.fixture
def clean_tm_records():
    test_text = "Unique text for translation memory testing."
    test_hash = hashlib.sha256(test_text.encode("utf-8")).hexdigest()
    
    # Setup: ensure the test key hash does not exist in the db
    db = SessionLocal()
    db.query(TranslationMemory).filter(TranslationMemory.source_hash == test_hash).delete()
    db.commit()
    db.close()
    
    yield test_text, test_hash
    
    # Teardown: clean up after the test
    db = SessionLocal()
    db.query(TranslationMemory).filter(TranslationMemory.source_hash == test_hash).delete()
    db.commit()
    db.close()

def test_translation_memory_caching_flow(clean_tm_records):
    test_text, test_hash = clean_tm_records
    
    # Khởi tạo GeminiTranslator
    translator = GeminiTranslator()
    
    # Mock phương thức _translate_chunk_api thực tế
    mock_api = MagicMock(return_value="Bản dịch đã được cache thành công.")
    
    with patch.object(translator, '_translate_chunk_api', mock_api):
        # 1. Dịch lần đầu: Cache Miss
        context = {
            "api_key": "real-test-api-key",  # Không bắt đầu bằng "fake-" để cache được bật
            "model": "gemini-1.5-flash",
            "source_lang": "English",
            "target_lang": "Vietnamese"
        }
        
        result1 = translator.translate_chunk(test_text, context)
        
        assert result1 == "Bản dịch đã được cache thành công."
        mock_api.assert_called_once_with(test_text, context)
        
        # Kiểm tra dữ liệu đã được lưu trữ trong SQLite
        db = SessionLocal()
        record = db.query(TranslationMemory).filter(TranslationMemory.source_hash == test_hash).first()
        assert record is not None
        assert record.source_text == test_text
        assert record.target_text == "Bản dịch đã được cache thành công."
        db.close()
        
        # Reset mock call count để kiểm tra cho lần thứ hai
        mock_api.reset_mock()
        
        # 2. Dịch lần hai: Cache Hit
        result2 = translator.translate_chunk(test_text, context)
        
        assert result2 == "Bản dịch đã được cache thành công."
        # Mock API không được phép gọi vì đã lấy từ Cache (DB) ra
        mock_api.assert_not_called()
