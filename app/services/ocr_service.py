import base64
import json
import re
from typing import Optional
import uuid
from loguru import logger
from mistralai import Mistral

from app.services.price_list_service import PriceListService

from app.core.config import settings
from app.models.document import DocumentResponse, DocumentItem, DocumentType
from app.services.llms.llm_factory import LLMFactory

openai_llm = LLMFactory.get_instance("openai")
llm = openai_llm
# from ..core.config import settings
# from ..models.document import DocumentResponse, DocumentItem
from tqdm import tqdm
import aiohttp
# from app.services.price_list_service import PriceListService

logger.add(
    "ocr_service.log",
    encoding="utf-8",
    rotation="10MB",
    compression="zip",
    format="{time}|{file}:{line}|{level} {message}",
    level="INFO",
)


class OCRService:
    def __init__(self):
        self._client = Mistral(
            api_key=settings.MISTRAL_API_KEY, timeout_ms=300000
            
        )  # 5 минут
        self._results = {}  # Временное хранилище результатов
        self.progress_bars = {}
    
    def update_progress_bar(self, progress_bar_id: str, text: str, processed:int, total:int):
        self.progress_bars[progress_bar_id] = {
            'text': text,
            'processed': processed,
            'total': total
        }
    
    def get_progress_bar(self, progress_bar_id: str) -> dict:
        return self.progress_bars.get(progress_bar_id, None)
    
    def encode_image(self, image_path):
        """Encode the image to base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except FileNotFoundError:
            print(f"Error: The file {image_path} was not found.")
            return None
        except Exception as e:  # Added general exception handling
            print(f"Error: {e}")
            return None

    async def send_mistral_document_batch(self, pages, progress_bar_id: str = None):
        all_text = []
        count_pages = 0
        self.update_progress_bar(progress_bar_id, "Получение товаров из документа ", 14, 100)
        max_percent_is_step=90
        now_percent_step=self.progress_bars[progress_bar_id]['processed']
        max_percent_step=max_percent_is_step - now_percent_step
        percent_step=round(max_percent_step/len(pages),1)
        for page in tqdm(
            pages, desc="Обработка страниц из документа (Mistral API)"
        ):
            self.update_progress_bar(progress_bar_id, "Получение товаров из документа ", percent_step*count_pages, 100)
            if count_pages >= 20:
                print(all_text)
                return all_text
            
            # continue
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "найди все товары и верни их в виде списка в формате json 'Наименование': наименование, 'Количество': количество, 'Ед.изм.': ед.изм.",
                        },
                        {"type": "text", "text": page.markdown},
                    ],
                }
            ]
            # logger.debug(f"Сообщения для API: {messages}")
            # Get the chat response
            # chat_response = await self._client.chat.complete_async(
            #     model="mistral-large-latest", messages=messages, max_tokens=40000
            # )

            # # Print the content of the response
            # text = chat_response.choices[0].message.content

            response = await llm.chat_completion(messages=messages)
            text=response['text']
            prepared_text = self.prepare_text_anserw_to_dict(text)
            logger.debug(f"Обработанная страница: {prepared_text}")
            if prepared_text:
                all_text.extend(prepared_text)
            count_pages += 1

        return all_text

    def prepare_text_anserw_to_dict(self, text: str) -> list:
        """
        Извлекает список товаров из текста, содержащего JSON-блок

        Args:
            text: Исходный текст с JSON-блоком

        Returns:
            list: Список словарей с товарами или None при ошибке
        """
        try:
            # Ищем JSON-блок между ```json и ```
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            
            # Если не нашли в формате ```json```, пробуем найти просто JSON в тексте
            if not json_match:
                # Пробуем найти JSON-массив в тексте напрямую
                text=text.replace("'",'"')
                data=json.loads(text)
                return data
                
            json_str = json_match.group(0) if not json_match.groups() else json_match.group(1)
            data = json.loads(json_str)

            if not isinstance(data, list):
                raise TypeError("JSON не содержит список")

            return data

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Ошибка извлечения списка: {str(e)}")
            return None

    async def process_document(
        self, file_path: str, original_filename: str, file_type: str = None, progress_bar_id: str = None
    ) -> DocumentResponse:
        """Обработка документа или изображения с использованием Mistral API"""
        # try:
        # Определяем расширение файла, если тип не передан явно
        if not file_type:
            file_ext = original_filename.split(".")[-1].lower()
            if file_ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                file_type = DocumentType.IMAGE
            elif file_ext == "pdf":
                file_type = DocumentType.PDF
            else:
                file_type = DocumentType.PDF  # По умолчанию PDF
        self.update_progress_bar(progress_bar_id, "Обработка документа", 10, 100)
        # Обработка в зависимости от типа файла
        if file_type == DocumentType.IMAGE:
            return await self.process_image(file_path, original_filename, progress_bar_id)

        # Иначе обрабатываем как документ
        # Загрузка файла в Mistral
        self.update_progress_bar(progress_bar_id, "Загрузка файла в Mistral", 11, 100)
        
        
        uploaded_file = await self._client.files.upload_async(
            file={
                "file_name": original_filename,
                "content": open(file_path, "rb"),
            },
            purpose="ocr",
        )
        logger.debug(f"Загруженный файл: {uploaded_file}")
        self.update_progress_bar(progress_bar_id, "Получение подписанного URL для доступа к файлу", 12, 100)
        #
        # 
        #  Получение подписанного URL для доступа к файлу
        signed_url = await self._client.files.get_signed_url_async(
            file_id=uploaded_file.id
        )
        logger.debug(f"Подписанный URL: {signed_url}")
        
        
        self.update_progress_bar(progress_bar_id, "Обработка документа через OCR", 13, 100)
        # Обработка документа через OCR
        ocr_response = await self._client.ocr.process_async(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url,
            },
            # include_image_base64=True
        )

        logger.debug(f"Обработанный документ: {ocr_response}")
        self.update_progress_bar(progress_bar_id, "Обработка страниц из документа (Mistral API)", 14, 100)
        all_texts = await self.send_mistral_document_batch(ocr_response.pages)
        products = all_texts
        print(products)
        # for text in all_texts:
        #     try:
        #         # Пытаемся распарсить JSON
        #      products = self.prepare_text_anserw_to_dict(text)
        #     except json.JSONDecodeError as e:
        #         # Если не удалось распарсить JSON, возвращаем текст как есть
        #         logger.warning(f"Не удалось распарсить JSON: {str(e)}, возвращаем текст как есть")
        #         # Создаем простой формат для отображения
        #         continue
        #         # products = [{"Наименование": text, "Количество": "", "Ед.изм.": ""}]

        document_response = DocumentResponse(
            id=uploaded_file.id,
            original_filename=original_filename,
            items=[
                DocumentItem(
                    text=item
                    if isinstance(item, str)
                    else json.dumps(item, ensure_ascii=False)
                )
                for item in products
            ],
        )

        # Сохранение результата
        self._results[uploaded_file.id] = document_response

        return document_response

        # except Exception as e:
        #     logger.error(f"Ошибка при обработке документа {original_filename}: {str(e)}")
        #     raise

    async def process_image(
        self, file_path: str, original_filename: str, progress_bar_id: str = None
    ) -> DocumentResponse:
        """Обработка изображения с использованием Mistral API"""
        self.update_progress_bar(progress_bar_id, "Загрузка изображения в Mistral", 10, 100)
        
        # uploaded_pdf = await self._client.files.upload_async(
        #     file={
        #         "file_name": original_filename,
        #         "content": open(file_path, "rb"),
        #     },
        #     purpose="ocr",
        # )
        # await self._client.files.retrieve_async(file_id=uploaded_pdf.id)
        self.update_progress_bar(progress_bar_id, "Получение подписанного URL для доступа к файлу", 11, 100)
        # signed_url = await self._client.files.get_signed_url_async(
        #     file_id=uploaded_pdf.id
        # )
        self.update_progress_bar(progress_bar_id, "Получение товаров из изображения", 12, 100)
        # messages = [
        #     {
        #         "role": "user",
        #         "content": [
        #             {
        #                 "type": "text",
        #                 "text": 'найди все позиции и верни их в виде списка в формате json "Наименование": наиминование, "Количество": количество, "Ед.изм.": ед.изм. даже если это 1 элемент то верни 1 элемент' ,
        #             },
        #             {"type": "image_url", "image_url": signed_url.url},
        #         ],
        #     }
        # ]

        # Get the chat response
        # chat_response = await self._client.chat.complete_async(
        #     model="pixtral-12b-2409", messages=messages
        # )

        # # Print the content of the response
        # products = chat_response.choices[0].message.content
        prompt="найди все позиции и верни их в виде списка в формате json 'Наименование': наименование, 'Количество': количество, 'Ед.изм.': ед.изм. даже если это 1 элемент то верни 1 элемент"
        response = await llm.image_to_text(file_path, prompt)
        text=response['text']


        logger.debug(f"Полученный ответ от API: {text}")
        products = self.prepare_text_anserw_to_dict(text)
        
        price_list_service = PriceListService()
        products = await price_list_service.find_matching_items(products, self.progress_bars, progress_bar_id)

            
        documentID_UUID=uuid.uuid4().hex
        document_response = DocumentResponse(
        id=documentID_UUID,
        original_filename=original_filename,
        items=[
            DocumentItem(
                text=item
                if isinstance(item, str)
                else json.dumps(item, ensure_ascii=False)
            )
            for item in products
            ],
        )

        # Сохранение результата
        self._results[documentID_UUID] = document_response

        return document_response

        

    def get_result(self, document_id: str) -> Optional[DocumentResponse]:
        """Получение результата обработки по ID документа"""
        return self._results.get(document_id)


# Создание экземпляра сервиса
ocr_service = OCRService()
