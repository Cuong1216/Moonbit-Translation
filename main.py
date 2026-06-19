import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from api.routes import router as api_router

app = FastAPI(
    title="Gemini Novel Translator & Glossary",
    description="Web App Local chuyên dịch tiểu thuyết và quản lý thuật ngữ bằng Google Gemini API",
    version="1.0.0"
)

# Đăng ký các API Routes
app.include_router(api_router)

# Cấu hình mount thư mục static để phục vụ CSS, JS, Images
# Thư mục static phải tồn tại trước khi khởi chạy
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    """
    Render trang index.html từ thư mục templates.
    Sử dụng FileResponse để phục vụ trực tiếp file HTML tĩnh một cách nhanh chóng.
    """
    template_path = os.path.join("templates", "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path)
    return {"error": "Trang index.html không tồn tại trong thư mục templates."}

@app.get("/api/health")
async def health_check():
    """
    API kiểm tra trạng thái hoạt động của ứng dụng.
    """
    has_api_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "ok",
        "gemini_api_key_configured": has_api_key,
        "message": "FastAPI backend is running smoothly!"
    }

if __name__ == "__main__":
    import uvicorn
    # Chạy ứng dụng bằng uvicorn khi thực thi trực tiếp file main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
