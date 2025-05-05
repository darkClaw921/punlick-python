import json
import re
from typing import Optional
from loguru import logger
from mistralai import Mistral

from app.core.config import settings
from app.models.document import DocumentResponse, DocumentItem
from app.services.price_list_service import PriceListService
from app.services.llms.llm_factory import LLMFactory

openai_llm = LLMFactory.get_instance("openai")
llm = openai_llm

logger.add(
    "chat_service.log",
    encoding="utf-8",
    rotation="10MB",
    compression="zip",
    format="{time}|{file}:{line}|{level} {message}",
    level="INFO",
)


class ChatService:
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

            if not json_match:
                text=text.replace("'",'"')
                data=json.loads(text)
                return data

            json_str = json_match.group(1)
            data = json.loads(json_str)

            if not isinstance(data, list):
                raise TypeError("JSON не содержит список")

            return data

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Ошибка извлечения списка: {str(e)}")
            return None

    async def process_chat_message(
        self, message_text: str, message_id: str, 
    ) -> DocumentResponse:
        """Обработка текстового сообщения из чата"""
        
        from chromaWork import ChromaWork
        self.update_progress_bar(message_id, "Распознование позиций из текстового сообщения", 0, 100)
        try:
            logger.debug(f"Обработка текстового сообщения: {message_text}")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """найди все товары и верни их в виде списка в формате json "Наименование","Количество","Ед.изм." """,
                        },
                        {"type": "text", "text": message_text},
                    ],
                }
            ]

            # Получаем ответ от API
            # chat_response = await self._client.chat.complete_async(
            #     model="mistral-large-latest", messages=messages
            # )
            
            # Получаем содержимое ответа
            # text = chat_response.choices[0].message.content
            response = await llm.chat_completion(messages=messages, model='gpt-4.1-nano-2025-04-14')
            text = response['text']
            logger.debug(f"Полученный ответ от API: {text}")
            text = self.prepare_text_anserw_to_dict(text)
            self.update_progress_bar(message_id, "Переименование позиций", 20, 100)
            price_list_service = PriceListService()
            products = await price_list_service.find_matching_items(text, self.progress_bars, message_id)
            # self.update_progress_bar(message_id, "Обработка текстового сообщения", 20, 100)
            document_response = DocumentResponse(
                id=message_id,
                original_filename=f"chat_message_{message_id}",
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
            self._results[message_id] = document_response

            return document_response

        except Exception as e:
            logger.error(
                f"Ошибка при обработке текстового сообщения {message_id}: {str(e)}"
            )
            raise

    def get_result(self, message_id: str) -> Optional[DocumentResponse]:
        """Получение результата обработки по ID сообщения"""
        return self._results.get(message_id)


# Создание экземпляра сервиса
chat_service = ChatService()
