import os
import shutil
import logging
from typing import List
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    Request,
)
from fastapi.responses import FileResponse
import time
import uuid
from pydantic import BaseModel

from app.core.config import settings
from app.models.document import (
    DocumentResponse,
    ExportResponse,
    PriceListResponse,
    PriceListSearchQuery,
)
from app.services.ocr_service import ocr_service
from app.services.chat_service import chat_service
from app.services.export_service import export_service
from app.services.xlsx_service import xlsx_service
from app.services.price_list_service import price_list_service

router = APIRouter()
logger = logging.getLogger(__name__)


# Модель для запроса текстового сообщения
class ChatMessageRequest(BaseModel):
    text: str


# Создаем директорию для загрузок, если она не существует
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    file_type: str = Form(None),
    background_tasks: BackgroundTasks = None,
):
    """Загрузка и обработка документа или изображения"""

    start_time = time.time()
    client_host = request.client.host

    # Проверка расширения файла
    file_ext = file.filename.split(".")[-1].lower()

    # Для документов поддерживаем только pdf и xlsx
    allowed_doc_extensions = ["pdf", "xlsx"]
    allowed_img_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]

    # Определяем тип файла на основе расширения и переданного параметра
    is_image = file_type == "image" or file_ext in allowed_img_extensions
    is_xlsx = file_ext == "xlsx"

    # Проверяем поддержку типа файла
    if is_image and file_ext not in allowed_img_extensions:
        logger.warning(
            f"Попытка загрузки изображения с неподдерживаемым расширением {file_ext} от {client_host}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат изображения. Разрешены: {', '.join(allowed_img_extensions)}",
        )
    elif not is_image and file_ext not in allowed_doc_extensions:
        logger.warning(
            f"Попытка загрузки документа с неподдерживаемым расширением {file_ext} от {client_host}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат документа. Разрешены: {', '.join(allowed_doc_extensions).upper()}",
        )

    try:
        # Сохраняем файл
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(
            f"Файл {file.filename} загружен от {client_host}, размер: {os.path.getsize(file_path)} байт, тип: {'изображение' if is_image else 'документ'}"
        )

        # Обрабатываем документ или изображение
        if is_image:
            # Обработка изображения
            result = await ocr_service.process_image(file_path, file.filename)
            logger.info(f"Обработка изображения {file.filename} запущена")
        elif is_xlsx:
            # Обработка XLSX файла
            result = await xlsx_service.process_xlsx_file(
                file_path, file.filename
            )
            logger.info(f"Обработка XLSX файла {file.filename} запущена")
        else:
            # Обработка PDF документа
            result = await ocr_service.process_document(
                file_path, file.filename
            )

        # # Обогащаем результаты данными из векторной базы
        # if result and result.items:
        #     # Устанавливаем порог сходства (можно настроить)
        #     similarity_threshold = 0.7
            
        #     # Ищем соответствия в векторной базе данных
        #     enriched_items = await price_list_service.find_matching_items(
        #         result.items, similarity_threshold
        #     )
            
        #     # Обновляем элементы в результате
        #     result.items = enriched_items
            
        #     logger.info(
        #         f"Обогащение результатов из векторной базы выполнено для {len(result.items)} элементов"
        #     )

        # processing_time = time.time() - start_time
        # logger.info(
        #     f"Обработка файла {file.filename} завершена за {processing_time:.2f} сек., распознано {len(result.items)} элементов"
        # )

        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке файла {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при обработке файла: {str(e)}"
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Получение результатов обработки документа по ID"""

    # Проверяем сначала в ocr_service
    result = ocr_service.get_result(document_id)

    # Если не найдено в ocr_service, проверяем в xlsx_service
    if not result and document_id.startswith("xlsx_"):
        result = xlsx_service.get_result(document_id)

    if not result:
        logger.warning(
            f"Попытка получения несуществующего документа с ID {document_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Документ с ID {document_id} не найден"
        )

    return result


@router.post("/documents/{document_id}/export", response_model=ExportResponse)
async def export_document(document_id: str):
    """Экспорт результатов обработки в XLSX"""

    # Получаем результат обработки сначала из ocr_service
    result = ocr_service.get_result(document_id)

    # Если не найдено в ocr_service, проверяем в xlsx_service
    if not result and document_id.startswith("xlsx_"):
        result = xlsx_service.get_result(document_id)

    if not result:
        logger.warning(
            f"Попытка экспорта несуществующего документа с ID {document_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Документ с ID {document_id} не найден"
        )

    try:
        # Экспортируем в XLSX
        start_time = time.time()
        export_filename = await export_service.export_to_xlsx(result)

        processing_time = time.time() - start_time
        logger.info(
            f"Экспорт документа {result.original_filename} (ID: {document_id}) в файл {export_filename} завершен за {processing_time:.2f} сек."
        )

        return ExportResponse(
            export_filename=export_filename,
            download_url=f"/api/exports/{export_filename}",
        )
    except Exception as e:
        logger.error(f"Ошибка при экспорте документа {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при экспорте документа: {str(e)}"
        )


@router.get("/exports/{filename}")
async def download_export(filename: str):
    """Скачивание экспортированного файла"""

    file_path = os.path.join(settings.EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        logger.warning(f"Попытка скачивания несуществующего файла {filename}")
        raise HTTPException(
            status_code=404, detail=f"Файл {filename} не найден"
        )

    logger.info(f"Скачивание файла {filename}")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/chat/message", response_model=DocumentResponse)
async def process_chat_message(message: ChatMessageRequest):
    """Обработка текстового сообщения из чата"""
    try:
        # Генерируем уникальный ID для сообщения
        message_id = str(uuid.uuid4())

        start_time = time.time()

        # Обрабатываем сообщение
        result = await chat_service.process_chat_message(
            message.text, message_id
        )

        # Обогащаем результаты данными из векторной базы
        if result and result.items:
            # Устанавливаем порог сходства (можно настроить)
            similarity_threshold = 0.7
            
            # Ищем соответствия в векторной базе данных
            enriched_items = await price_list_service.find_matching_items(
                result.items, similarity_threshold
            )
            
            # Обновляем элементы в результате
            result.items = enriched_items
            
            logger.info(
                f"Обогащение результатов чата из векторной базы выполнено для {len(result.items)} элементов"
            )

        processing_time = time.time() - start_time
        logger.info(
            f"Обработка текстового сообщения завершена за {processing_time:.2f} сек., распознано {len(result.items)} элементов"
        )

        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке текстового сообщения: {str(e)}",
        )


@router.get("/chat/messages/{message_id}", response_model=DocumentResponse)
async def get_chat_message(message_id: str):
    """Получение результатов обработки текстового сообщения по ID"""

    result = chat_service.get_result(message_id)
    if not result:
        logger.warning(
            f"Попытка получения несуществующего сообщения с ID {message_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Сообщение с ID {message_id} не найдено"
        )

    return result


@router.post(
    "/chat/messages/{message_id}/export", response_model=ExportResponse
)
async def export_chat_message(message_id: str):
    """Экспорт результатов обработки текстового сообщения в XLSX"""

    # Получаем результат обработки
    result = chat_service.get_result(message_id)
    if not result:
        logger.warning(
            f"Попытка экспорта несуществующего сообщения с ID {message_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Сообщение с ID {message_id} не найдено"
        )

    try:
        # Экспортируем в XLSX
        start_time = time.time()
        export_filename = await export_service.export_to_xlsx(result)

        processing_time = time.time() - start_time
        logger.info(
            f"Экспорт сообщения (ID: {message_id}) в файл {export_filename} завершен за {processing_time:.2f} сек."
        )

        return ExportResponse(
            export_filename=export_filename,
            download_url=f"/api/exports/{export_filename}",
        )
    except Exception as e:
        logger.error(f"Ошибка при экспорте сообщения {message_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при экспорте сообщения: {str(e)}"
        )


@router.post("/price-lists/upload", response_model=PriceListResponse)
async def upload_price_list(
    request: Request,
    file: UploadFile = File(...),
    supplier_id: str = Form(None),
    replace_existing: bool = Form(False),
    clear_by_supplier: bool = Form(False),
):
    """Загрузка и обработка прайс-листа в векторную базу данных"""

    start_time = time.time()
    client_host = request.client.host

    # Проверка расширения файла
    file_ext = file.filename.split(".")[-1].lower()
    allowed_extensions = ["xlsx", "xls", "csv", "json"]

    if file_ext not in allowed_extensions:
        logger.warning(
            f"Попытка загрузки прайс-листа с неподдерживаемым расширением {file_ext} от {client_host}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат прайс-листа. Разрешены: {', '.join(allowed_extensions)}",
        )

    try:
        # Сохраняем файл
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(
            f"Прайс-лист {file.filename} загружен от {client_host}, размер: {os.path.getsize(file_path)} байт"
        )

        # Обрабатываем прайс-лист
        result = await price_list_service.update_price_list_collection(
            file_path=file_path,
            original_filename=file.filename,
            replace_existing=replace_existing,
            clear_by_supplier=clear_by_supplier,
            supplier_id=supplier_id
        )

        processing_time = time.time() - start_time
        logger.info(
            f"Обработка прайс-листа {file.filename} завершена за {processing_time:.2f} сек., загружено {result.total_items} товаров из {result.categories_count} категорий"
        )

        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке прайс-листа {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при обработке прайс-листа: {str(e)}"
        )


@router.post("/price-lists/search", response_model=List[dict])
async def search_price_list_items(query: PriceListSearchQuery):
    """Поиск товаров в векторной базе данных по запросу"""
    try:
        start_time = time.time()
        
        results = await price_list_service.search_similar_items(
            query=query.query,
            limit=query.limit,
            supplier_id=query.supplier_id,
            min_price=query.min_price,
            max_price=query.max_price,
            category=query.category
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"Поиск по запросу '{query.query}' завершен за {processing_time:.2f} сек., найдено {len(results)} товаров"
        )
        
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске товаров: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при поиске товаров: {str(e)}"
        )


@router.get("/price-lists/{upload_id}/status")
async def get_price_list_upload_status(upload_id: str):
    """Получение статуса загрузки прайс-листа"""
    try:
        status = price_list_service.get_upload_status(upload_id)
        if not status:
            raise HTTPException(
                status_code=404, detail=f"Процесс загрузки с ID {upload_id} не найден"
            )
        
        return status
    except Exception as e:
        logger.error(f"Ошибка при получении статуса загрузки прайс-листа {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении статуса загрузки: {str(e)}"
        )
