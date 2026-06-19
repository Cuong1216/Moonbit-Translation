import logging
import google.generativeai as genai

logger = logging.getLogger("ModelHelper")

def resolve_model_name(requested_model: str, api_key: str = None) -> str:
    """
    Tự động truy vấn danh sách các model khả dụng cho API Key của người dùng.
    Nếu model được yêu cầu không được hỗ trợ hoặc bị lỗi 404, hàm sẽ tìm kiếm
    và chọn một model thay thế (fallback) phù hợp có sẵn (ví dụ: gemini-2.0-flash, gemini-1.5-flash-latest, ...).
    
    :param requested_model: Tên model yêu cầu (ví dụ: 'gemini-1.5-flash').
    :param api_key: API Key để truy vấn (nếu có).
    :return: Tên model khả dụng hoặc model được yêu cầu ban đầu làm fallback.
    """
    if api_key:
        genai.configure(api_key=api_key)
        
    try:
        # Lấy danh sách models khả dụng cho khóa API này
        available_models = [m.name for m in genai.list_models()]
        logger.info(f"Các model khả dụng trên API Key: {available_models}")
        
        # Chuẩn hóa tên model yêu cầu để đối chiếu
        req_name = requested_model.lower().strip()
        req_full = req_name if req_name.startswith("models/") else f"models/{req_name}"
        
        # 1. Nếu tìm thấy chính xác model được yêu cầu, sử dụng nó
        for m in available_models:
            if m.lower() == req_full:
                return requested_model
                
        # 2. Nếu không tìm thấy chính xác, tìm model chứa tên được yêu cầu (ví dụ: 'gemini-1.5-flash-latest')
        for m in available_models:
            short_name = m.replace("models/", "")
            if req_name in short_name.lower() or short_name.lower() in req_name:
                logger.info(f"Tìm thấy model tương đồng: {short_name} thay thế cho {requested_model}")
                return short_name
                
        # 3. Tìm bất kỳ model nào có chữ 'flash' trong tên để tối ưu hóa tốc độ và chi phí
        flash_models = [m.replace("models/", "") for m in available_models if "flash" in m.lower()]
        if flash_models:
            logger.info(f"Không tìm thấy {requested_model}. Tự động chọn model Flash khả dụng: {flash_models[0]}")
            return flash_models[0]
            
        # 4. Nếu không có 'flash', tìm model bất kỳ có chữ 'gemini'
        gemini_models = [m.replace("models/", "") for m in available_models if "gemini" in m.lower()]
        if gemini_models:
            logger.info(f"Tự động chọn model Gemini khả dụng: {gemini_models[0]}")
            return gemini_models[0]
            
        # 5. Fallback cuối cùng
        if available_models:
            first_model = available_models[0].replace("models/", "")
            logger.info(f"Chọn model đầu tiên trong danh sách khả dụng: {first_model}")
            return first_model
            
    except Exception as e:
        logger.warning(
            f"Không thể truy vấn danh sách model từ API: {e}. "
            f"Sử dụng tên model yêu cầu mặc định: {requested_model}"
        )
        
    return requested_model
