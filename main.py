import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Khởi tạo cơ sở dữ liệu SQLite
from database import init_db
init_db()

from api.routes import router as api_router

app = FastAPI(
    title="Moonbit Translation",
    description="Web App Local chuyên dịch tiểu thuyết và quản lý thuật ngữ bằng Google Gemini API và Local Ollama",
    version="1.0.0"
)

# Đăng ký các API Routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    import httpx
    import logging
    logger = logging.getLogger("NovelTranslator")
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get("http://localhost:11434/")
            if response.status_code == 200:
                logger.info("Ollama is running. Local AI is ready to use!")
                print("Ollama is running. Local AI is ready to use!")
    except Exception:
        pass

# Cấu hình Custom StaticFiles để vô hiệu hóa hoàn toàn cache trình duyệt cho static files
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Cấu hình mount thư mục static để phục vụ CSS, JS, Images
# Thư mục static phải tồn tại trước khi khởi chạy
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    """
    Render trang index.html từ thư mục templates.
    Sử dụng FileResponse để phục vụ trực tiếp file HTML tĩnh một cách nhanh chóng.
    """
    template_path = os.path.join("templates", "index.html")
    if os.path.exists(template_path):
        return FileResponse(
            template_path, 
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
        )
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
