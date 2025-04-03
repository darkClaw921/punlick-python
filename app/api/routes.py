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
from fastapi.responses import FileResponse, JSONResponse
import time
import uuid
from pydantic import BaseModel
import hashlib
import glob
import asyncio

from app.core.config import settings
# from app.core.logger import logger
from app.models.document import (
    DocumentResponse,
    ExportResponse,
    PriceListResponse,
    PriceListSearchQuery,
)
from app.models.rules import (
    RulesFileResponse,
    RuleBlockResponse,
    RuleBlockUpdateRequest,
    RuleTypeResponse,
    NewRuleBlockRequest,
    NewRuleFileRequest
)
from app.services.ocr_service import ocr_service
from app.services.chat_service import chat_service
from app.services.export_service import export_service
from app.services.xlsx_service import xlsx_service
from app.services.price_list_service import price_list_service
from app.services.rules_service import rules_service
from chromaWork import ChromaWork

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


# Маршруты для работы с правилами
@router.get("/rules/types", response_model=List[RuleTypeResponse])
async def get_rule_types():
    """Получение списка доступных типов правил"""
    type_dict = rules_service.get_available_rule_types()
    
    types = [
        RuleTypeResponse(id=type_id, name=type_name)
        for type_id, type_name in type_dict.items()
    ]
    
    return types


@router.get("/rules/block/{block_id}", response_model=RuleBlockResponse)
async def get_rule_block(block_id: str):
    """Получение блока правил по ID"""
    rule_block = rules_service.get_rule_block(block_id)
    if not rule_block:
        raise HTTPException(status_code=404, detail=f"Блок правил с ID {block_id} не найден")
    
    # Преобразуем модель RuleBlock в RuleBlockResponse
    return RuleBlockResponse(
        id=rule_block.id,
        title=rule_block.title,
        content=rule_block.content
    )


@router.put("/rules/block/{block_id}", response_model=RuleBlockResponse)
async def update_rule_block(block_id: str, rule_update: RuleBlockUpdateRequest):
    """Обновление блока правил"""
    rule_block = rules_service.get_rule_block(block_id)
    if not rule_block:
        raise HTTPException(status_code=404, detail=f"Блок правил с ID {block_id} не найден")
    
    # Сохраняем значения перед обновлением
    original_title = rule_block.title
    original_content = rule_block.content
    
    # Определяем новые значения
    new_title = rule_update.title if rule_update.title is not None else original_title
    new_content = rule_update.content if rule_update.content is not None else original_content
    
    success = rules_service.update_rule_block(
        block_id, 
        title=rule_update.title, 
        content=rule_update.content
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Не удалось обновить блок правил")
    
    # Создаем ответ на основе обновленных данных
    return RuleBlockResponse(
        id=block_id,  # Используем тот же ID для ответа
        title=new_title,
        content=new_content
    )


@router.get("/rules/{file_type}", response_model=RulesFileResponse)
async def get_rules(file_type: str = "round"):
    """Получение правил из файла по типу"""
    try:
        rules_file = rules_service.parse_rules_file(file_type)
        
        # Преобразуем модели RuleBlock в RuleBlockResponse
        blocks_response = [
            RuleBlockResponse(id=block.id, title=block.title, content=block.content)
            for block in rules_file.blocks
        ]
        
        return RulesFileResponse(blocks=blocks_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Ошибка при получении правил типа {file_type}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при получении правил: {str(e)}"
        )


@router.get("/rules", response_model=RulesFileResponse)
async def get_default_rules():
    """Получение правил из файла по умолчанию (круглые)"""
    return await get_rules("round")


@router.post("/rules/block", response_model=RuleBlockResponse)
async def create_rule_block(rule_request: NewRuleBlockRequest):
    """Создание нового блока правил"""
    try:
        new_block = rules_service.create_new_rule_block(
            file_type=rule_request.file_type,
            title=rule_request.title,
            content=rule_request.content
        )
        
        if not new_block:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать новый блок правил"
            )
        
        # Преобразуем модель RuleBlock в RuleBlockResponse
        return RuleBlockResponse(
            id=new_block.id,
            title=new_block.title,
            content=new_block.content
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Ошибка при создании нового блока правил: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании нового блока правил: {str(e)}"
        )


@router.post("/rules/file", response_model=RuleTypeResponse)
async def create_rules_file(file_request: NewRuleFileRequest):
    """Создание нового файла правил"""
    try:
        success = rules_service.create_new_rules_file(
            file_type=file_request.file_type,
            file_name=file_request.file_name
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать новый файл правил"
            )
        
        return RuleTypeResponse(
            id=file_request.file_type,
            name=file_request.display_name
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Ошибка при создании нового файла правил: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании нового файла правил: {str(e)}"
        )


@router.delete("/rules/block/{block_id}")
async def delete_rule_block(block_id: str):
    """Удаление блока правил"""
    try:
        success = rules_service.delete_rule_block(block_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Блок правил с ID {block_id} не найден или не может быть удален"
            )
        
        return {"success": True, "message": "Блок правил успешно удален"}
    except Exception as e:
        logger.error(f"Ошибка при удалении блока правил: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении блока правил: {str(e)}"
        )


@router.post("/rules/reload")
async def reload_rules_files():
    """Перезагрузка файлов правил из директории"""
    try:
        rules_service.load_rule_files()
        return {"message": "Rules files reloaded successfully", "types": rules_service.get_available_rule_types()}
    except Exception as e:
        logger.error(f"Error reloading rules files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reloading rules files: {str(e)}")


@router.post("/chroma/reindex")
async def reindex_chroma(background_tasks: BackgroundTasks):
    try:
        # Генерируем уникальный ID для задачи
        reindex_id = str(uuid.uuid4())
        
        # Инициализируем статус индексации
        _reindex_statuses = {}
        if hasattr(price_list_service, '_upload_statuses'):
            _reindex_statuses = price_list_service._upload_statuses
        else:
            price_list_service._upload_statuses = _reindex_statuses
        
        _reindex_statuses[reindex_id] = {
            "status": "initiated",
            "percent_complete": 0,
            "processed_files": 0,
            "total_files": 0,
            "current_stage": "подготовка к индексации",
            "start_time": time.time(),
            "indexed_files": []
        }
        
        # Запускаем фоновую задачу
        background_tasks.add_task(
            perform_chroma_reindex, 
            reindex_id=reindex_id
        )
        
        return {
            "status": "started",
            "reindex_id": reindex_id,
            "message": "Переиндексация запущена. Используйте GET /api/chroma/reindex/{reindex_id}/status для отслеживания прогресса."
        }
    except Exception as e:
        logger.error(f"Ошибка при запуске переиндексации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске переиндексации: {str(e)}")

@router.get("/chroma/reindex/{reindex_id}/status")
async def get_reindex_status(reindex_id: str):
    """Получение статуса переиндексации"""
    try:
        if not hasattr(price_list_service, '_upload_statuses'):
            price_list_service._upload_statuses = {}
            
        _reindex_statuses = price_list_service._upload_statuses
        status = _reindex_statuses.get(reindex_id)
        
        if not status:
            raise HTTPException(
                status_code=404, detail=f"Процесс переиндексации с ID {reindex_id} не найден"
            )
        
        # Создаем копию статуса для безопасного изменения
        status_copy = status.copy()
        
        # Добавляем информацию о времени выполнения
        if 'start_time' in status_copy:
            elapsed_time = time.time() - status_copy["start_time"]
            status_copy["elapsed_time"] = f"{elapsed_time:.2f} сек."
        
        return status_copy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении статуса переиндексации {reindex_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении статуса переиндексации: {str(e)}"
        )

async def perform_chroma_reindex(reindex_id: str):
    """Фоновая задача для переиндексации Chroma"""
    if not hasattr(price_list_service, '_upload_statuses'):
        price_list_service._upload_statuses = {}
        
    _reindex_statuses = price_list_service._upload_statuses
    if reindex_id not in _reindex_statuses:
        _reindex_statuses[reindex_id] = {
            "status": "initiated",
            "percent_complete": 0,
            "processed_files": 0,
            "total_files": 0,
            "current_stage": "подготовка к индексации",
            "start_time": time.time(),
            "indexed_files": []
        }
        
    status = _reindex_statuses[reindex_id]
    
    try:
        # Проверяем, есть ли start_time, если нет - добавляем
        if 'start_time' not in status:
            status['start_time'] = time.time()
            
        # Получаем список всех файлов в директории rules
        rule_files = glob.glob("rules/*.txt") + glob.glob("rules/*[!.txt]")
        total_files = len(rule_files)
        
        # Обновляем статус
        status["status"] = "processing"
        status["total_files"] = total_files
        status["current_stage"] = "удаление старой коллекции"
        _reindex_statuses[reindex_id] = status
        
        # Удаляем существующую коллекцию
        chroma = ChromaWork('test')
        chroma.delete_collection()
        
        # Обновляем статус
        status["current_stage"] = "создание новой коллекции"
        _reindex_statuses[reindex_id] = status
        
        # Создаем новый экземпляр
        chroma = ChromaWork('test')
        
        # Индексируем файлы
        indexed_files = []
        for i, file_path in enumerate(rule_files):
            try:
                # Обновляем статус
                status["current_stage"] = f"индексация файла {os.path.basename(file_path)}"
                status["processed_files"] = i
                status["percent_complete"] = int((i / total_files) * 100) if total_files > 0 else 0
                _reindex_statuses[reindex_id] = status
                
                # Индексируем файл
                with open(file_path, "r") as file:
                    content = file.read()
                    await chroma.add_items(content)
                
                # Добавляем в список проиндексированных
                indexed_files.append(os.path.basename(file_path))
                status["indexed_files"] = indexed_files
                _reindex_statuses[reindex_id] = status
                
            except Exception as e:
                logger.error(f"Ошибка индексации файла {file_path}: {str(e)}")
                status["error"] = f"Ошибка при индексации файла {os.path.basename(file_path)}: {str(e)}"
                _reindex_statuses[reindex_id] = status
        
        # Обновляем финальный статус
        status["status"] = "completed"
        status["percent_complete"] = 100
        status["processed_files"] = total_files
        status["current_stage"] = "завершено"
        status["end_time"] = time.time()
        
        # Безопасно вычисляем elapsed_time
        if 'start_time' in status:
            status["elapsed_time"] = f"{status['end_time'] - status['start_time']:.2f} сек."
        else:
            status["elapsed_time"] = "время неизвестно"
            
        _reindex_statuses[reindex_id] = status
        
    except Exception as e:
        logger.error(f"Ошибка при переиндексации Chroma: {str(e)}")
        status["status"] = "error"
        status["error"] = str(e)
        status["current_stage"] = "ошибка"
        status["end_time"] = time.time()
        
        # Безопасно вычисляем elapsed_time
        if 'start_time' in status:
            status["elapsed_time"] = f"{status['end_time'] - status['start_time']:.2f} сек."
        else:
            status["elapsed_time"] = "время неизвестно"
            
        _reindex_statuses[reindex_id] = status
