import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения"""

    # Основные настройки
    APP_TITLE: str = "OCR Document Processor"
    APP_VERSION: str = "0.1.0"

    # Настройки API Mistral
    MISTRAL_API_URL: str = os.getenv(
        "MISTRAL_API_URL", "https://api.mistral.ai"
    )
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")

    # Модели Mistral
    MISTRAL_OCR_MODEL: str = os.getenv(
        "MISTRAL_OCR_MODEL", "mistral-ocr-latest"
    )
    MISTRAL_LLM_MODEL: str = os.getenv(
        "MISTRAL_LLM_MODEL", "mistral-small-latest"
    )
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # Настройки загрузки файлов
    UPLOAD_DIR: str = (
        "/Users/igorgerasimov/cursorWorkspace/punlick-python/uploads"
    )
    MAX_FILE_SIZE: int = int(
        os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024)
    )  # 10 MB по умолчанию
    ALLOWED_EXTENSIONS: set = {
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp",
        "tiff",
        "svg",
    }  # Расширенный список форматов изображений

    # Настройки экспорта
    EXPORT_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "exports"
    )

    # Настройки ChromaDB
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "vectordb")
    CHROMA_COLLECTION_NAME: str = os.getenv(
        "CHROMA_COLLECTION_NAME", "price_list"
    )

    class Config:
        env_file = ".env"


# Создаем директории, если они не существуют
os.makedirs(Settings().UPLOAD_DIR, exist_ok=True)
os.makedirs(Settings().EXPORT_DIR, exist_ok=True)
os.makedirs(Settings().CHROMA_DB_DIR, exist_ok=True)

# Экземпляр настроек
settings = Settings()
