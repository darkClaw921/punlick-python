import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.core.config import settings
from loguru import logger

# Настройка логирования
logger.add(
    "app.log",
    encoding="utf-8",
    rotation="10MB",
    compression="zip",
    format="{time}|{file}:{line}|{level} {message}",
    level="INFO",
)
# logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

app = FastAPI(
    title="OCR Document Processor",
    description="Приложение для обработки документов через OCR Mistral",
    version="0.1.0",
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR, html=True),
    name="uploads",
)

# Подключение шаблонов
templates = Jinja2Templates(directory="app/templates")

# Подключение маршрутов API
app.include_router(api_router, prefix="/api")


@app.get("/")
async def index(request: Request):
    """Главная страница приложения"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware для логирования запросов"""
    path = request.url.path
    method = request.method
    client = request.client.host if request.client else "unknown"

    logger.info(f"Request: {method} {path} - Client: {client}")

    response = await call_next(request)

    logger.info(f"Response: {method} {path} - Status: {response.status_code}")

    return response


@app.get("/uploads/{filename}")
async def serve_file(filename: str):
    """Прямая отдача файлов"""
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path)


if __name__ == "__main__":
    import uvicorn

    logger.info("Запуск приложения OCR Document Processor")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
