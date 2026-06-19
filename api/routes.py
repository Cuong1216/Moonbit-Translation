import os
import json
import docx
import tempfile
import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from typing import Dict, Optional

# Import các service nghiệp vụ
from services import file_extractor, glossary_builder, novel_translator

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APIRoutes")

router = APIRouter(prefix="/api", tags=["API"])

# Trạng thái tiến trình dịch toàn cục
active_task = {
    "task_id": None,
    "chunks": [],
    "translated_chunks": [],
    "current_chunk_idx": 0,
    "total_chunks": 0,
    "is_paused": False,
    "glossary": {},
    "api_key": None,
    "model": None,
    "source_lang": None,
    "target_lang": None,
    "provider": None
}

STATE_FILE = "translation_state.json"

def save_active_task_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(active_task, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi lưu file trạng thái dịch: {e}")

def load_active_task_state():
    global active_task
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                active_task.update(data)
                logger.info(f"Đã khôi phục trạng thái dịch trước đó: Task ID = {active_task['task_id']}, Tiến trình = {active_task['current_chunk_idx']}/{active_task['total_chunks']}")
        except Exception as e:
            logger.error(f"Lỗi đọc file trạng thái dịch: {e}")

# Khôi phục trạng thái khi module được tải
load_active_task_state()

# Pydantic models
class TranslateRequest(BaseModel):
    text: str
    glossary: Dict[str, str]
    api_key: Optional[str] = None
    model: str = "gemini-1.5-flash"
    temperature: float = 0.3
    source_lang: str = "Trung Quốc"
    target_lang: str = "Tiếng Việt"
    provider: str = "gemini"

class DownloadRequest(BaseModel):
    text: str
    format: str = "txt"  # "txt" hoặc "docx"
    filename: str = "dich_truyen"


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Nhận file từ người dùng, gọi FileExtractor để trích xuất text thuần 
    và trả về nội dung cho Frontend hiển thị.
    """
    filename = file.filename
    suffix = os.path.splitext(filename)[1].lower()
    
    if suffix not in [".docx", ".pdf", ".epub", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng tệp không được hỗ trợ. Chỉ hỗ trợ .docx, .pdf, .epub, .txt"
        )
        
    # Lưu tạm tệp tin vào đĩa để FileExtractor xử lý đường dẫn tệp
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi ghi file tạm thời: {str(e)}"
            )

    try:
        # Gọi extractor để lấy plain text
        extracted_text = file_extractor.extract_text(tmp_path, suffix)
        return {
            "filename": filename,
            "status": "success",
            "content": extracted_text
        }
    except Exception as e:
        logger.error(f"Lỗi trích xuất file {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trích xuất nội dung file: {str(e)}"
        )
    finally:
        # Xóa file tạm thời sau khi xử lý xong
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/build-glossary")
async def build_glossary_endpoint(
    source_file: UploadFile = File(...),
    translated_file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    """
    Nhận 2 file (gốc và dịch cũ), trích xuất văn bản,
    gọi glossary_builder để đối chiếu và trả về bảng thuật ngữ.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy Gemini API Key. Vui lòng thiết lập trong Cài đặt."
        )

    # Đọc tệp gốc cũ
    src_suffix = os.path.splitext(source_file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=src_suffix) as src_tmp:
        src_tmp.write(await source_file.read())
        src_path = src_tmp.name

    # Đọc tệp dịch cũ
    tgt_suffix = os.path.splitext(translated_file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=tgt_suffix) as tgt_tmp:
        tgt_tmp.write(await translated_file.read())
        tgt_path = tgt_tmp.name

    try:
        # Trích xuất text từ cả hai tệp
        source_text = file_extractor.extract_text(src_path, src_suffix)
        translated_text = file_extractor.extract_text(tgt_path, tgt_suffix)

        if not source_text.strip() or not translated_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Một hoặc cả hai tệp tin tải lên không chứa nội dung văn bản."
            )

        # Chạy glossary_builder
        glossary = glossary_builder.build_glossary(
            source_text=source_text,
            translated_text=translated_text,
            api_key=key
        )
        
        return {
            "status": "success",
            "glossary": glossary
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Lỗi xây dựng thuật ngữ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi phân tích thuật ngữ: {str(e)}"
        )
    finally:
        # Dọn dẹp file tạm
        for path in [src_path, tgt_path]:
            if os.path.exists(path):
                os.remove(path)


async def event_generator():
    total = active_task["total_chunks"]
    
    while active_task["current_chunk_idx"] < total:
        idx = active_task["current_chunk_idx"]
        
        # Kiểm tra xem có lệnh Pause không
        if active_task["is_paused"]:
            yield f"data: {json.dumps({
                'status': 'Đã tạm dừng dịch thuật.',
                'progress': int((idx / total) * 100),
                'event': 'paused',
                'current_chunk_idx': idx
            }, ensure_ascii=False)}\n\n"
            return
            
        chunk = active_task["chunks"][idx]
        progress = int((idx / total) * 100)
        
        yield f"data: {json.dumps({
            'status': f'Đang dịch đoạn {idx + 1}/{total}...',
            'progress': progress,
            'event': 'translating'
        }, ensure_ascii=False)}\n\n"
        
        try:
            translation = await asyncio.to_thread(
                novel_translator.translate_chunk,
                chunk,
                active_task["glossary"],
                active_task["api_key"],
                active_task["model"],
                active_task["source_lang"],
                active_task["target_lang"],
                active_task["provider"]
            )
            
            # Kiểm tra xem có bị tạm dừng trong quá trình call API không
            if active_task["is_paused"]:
                active_task["translated_chunks"].append(translation)
                active_task["current_chunk_idx"] += 1
                save_active_task_state()
                
                yield f"data: {json.dumps({
                    'status': f'Đoạn {idx + 1} đã dịch xong trước khi tạm dừng.',
                    'progress': int(((idx + 1) / total) * 100),
                    'event': 'chunk_completed',
                    'translated_chunk': translation
                }, ensure_ascii=False)}\n\n"
                
                yield f"data: {json.dumps({
                    'status': 'Đã tạm dừng dịch thuật.',
                    'progress': int(((idx + 1) / total) * 100),
                    'event': 'paused',
                    'current_chunk_idx': idx + 1
                }, ensure_ascii=False)}\n\n"
                return
            
            active_task["translated_chunks"].append(translation)
            active_task["current_chunk_idx"] += 1
            save_active_task_state()
            
            yield f"data: {json.dumps({
                'status': f'Hoàn thành đoạn {idx + 1}/{total}',
                'progress': int(((idx + 1) / total) * 100),
                'event': 'chunk_completed',
                'translated_chunk': translation
            }, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"Lỗi khi dịch đoạn {idx + 1}: {e}")
            yield f"data: {json.dumps({
                'status': f'Thất bại ở đoạn {idx + 1}: {str(e)}',
                'progress': progress,
                'event': 'error',
                'error': str(e)
            }, ensure_ascii=False)}\n\n"
            return

    # Hoàn tất dịch toàn bộ
    full_text = "\n\n".join(active_task["translated_chunks"])
    # Xóa file trạng thái khi đã dịch xong hoàn toàn
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
    active_task["task_id"] = None

    yield f"data: {json.dumps({
        'status': 'Dịch hoàn tất!',
        'progress': 100,
        'event': 'completed',
        'full_translation': full_text
    }, ensure_ascii=False)}\n\n"


@router.post("/translate")
async def translate_endpoint(request: TranslateRequest):
    """
    Dịch tiểu thuyết sử dụng cơ chế Server-Sent Events (SSE).
    Liên tục cập nhật tiến độ cho Frontend (ví dụ: đang dịch đoạn 5/10)
    và gửi kèm nội dung đoạn đã dịch xong.
    """
    provider = request.provider.strip().lower()
    
    # Lấy key tương ứng với từng provider
    key = request.api_key
    if not key:
        if provider == "gemini":
            key = os.getenv("GEMINI_API_KEY")
        elif provider == "claude":
            key = os.getenv("ANTHROPIC_API_KEY")
        elif provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY")

    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không tìm thấy API Key cho {request.provider}. Vui lòng thiết lập trong Cài đặt."
        )

    # Chia đoạn văn bản
    chunks = novel_translator.smart_chunking(request.text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Văn bản nguồn rỗng hoặc không thể chia nhỏ."
        )

    # Khởi tạo hoặc ghi đè active_task
    import uuid
    active_task.update({
        "task_id": str(uuid.uuid4()),
        "chunks": chunks,
        "translated_chunks": [],
        "current_chunk_idx": 0,
        "total_chunks": len(chunks),
        "is_paused": False,
        "glossary": request.glossary,
        "api_key": key,
        "model": request.model,
        "source_lang": request.source_lang,
        "target_lang": request.target_lang,
        "provider": provider
    })
    save_active_task_state()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/pause")
async def pause_endpoint():
    if active_task["task_id"] is None:
        raise HTTPException(status_code=400, detail="Không có tiến trình dịch thuật nào đang chạy.")
    active_task["is_paused"] = True
    save_active_task_state()
    return {
        "status": "success",
        "message": "Đã gửi yêu cầu tạm dừng.",
        "current_chunk_idx": active_task["current_chunk_idx"],
        "total_chunks": active_task["total_chunks"]
    }


@router.post("/resume")
async def resume_endpoint():
    if active_task["task_id"] is None:
        raise HTTPException(status_code=400, detail="Không có tiến trình nào để tiếp tục.")
    
    if not active_task["is_paused"]:
        return {"status": "ignored", "message": "Tiến trình dịch đang chạy, không cần resume."}
        
    active_task["is_paused"] = False
    save_active_task_state()
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/download")
async def download_file_endpoint(request: DownloadRequest):
    """
    Cho phép tải file text hoặc docx chứa kết quả sau khi dịch xong.
    Sử dụng BackgroundTask để dọn dẹp tệp tạm thời sau khi tải xong.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tải xuống rỗng."
        )

    # Đảm bảo tên file an toàn
    safe_filename = "".join([c for c in request.filename if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    if not safe_filename:
        safe_filename = "ban_dich"

    if request.format == "docx":
        # Tạo file Word docx
        doc = docx.Document()
        
        # Chia các đoạn văn theo dấu xuống dòng và ghi vào tệp docx
        for para in request.text.split("\n"):
            doc.add_paragraph(para)
            
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_path = tmp.name
        tmp.close()
        
        try:
            doc.save(tmp_path)
            
            # Đăng ký BackgroundTask xóa file tạm sau khi response được gửi xong
            cleanup_task = BackgroundTask(lambda: os.path.exists(tmp_path) and os.remove(tmp_path))
            
            return FileResponse(
                tmp_path,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"{safe_filename}.docx",
                background=cleanup_task
            )
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi tạo tệp tin Word: {str(e)}"
            )
    else:
        # Mặc định tải về file .txt
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
        tmp_path = tmp.name
        
        try:
            tmp.write(request.text)
            tmp.close()
            
            cleanup_task = BackgroundTask(lambda: os.path.exists(tmp_path) and os.remove(tmp_path))
            
            return FileResponse(
                tmp_path,
                media_type="text/plain",
                filename=f"{safe_filename}.txt",
                background=cleanup_task
            )
        except Exception as e:
            tmp.close()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi tạo tệp tin Text: {str(e)}"
            )
