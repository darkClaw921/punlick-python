import json
import re
from typing import Optional
from loguru import logger
from mistralai import Mistral

from app.core.config import settings
from app.models.document import DocumentResponse, DocumentItem

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
                raise ValueError("JSON-блок не найден в тексте")

            json_str = json_match.group(1)
            data = json.loads(json_str)

            if not isinstance(data, list):
                raise TypeError("JSON не содержит список")

            return data

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Ошибка извлечения списка: {str(e)}")
            return None

    async def process_chat_message(
        self, message_text: str, message_id: str
    ) -> DocumentResponse:
        """Обработка текстового сообщения из чата"""
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
            chat_response = self._client.chat.complete(
                model="mistral-large-latest", messages=messages
            )

            # Получаем содержимое ответа
            text = chat_response.choices[0].message.content
            logger.debug(f"Полученный ответ от API: {text}")

            try:
                # Пытаемся распарсить JSON
                products = self.prepare_text_anserw_to_dict(text)
                if not products:
                    # Если не удалось распарсить JSON или результат пустой, создаем пустой список
                    products = []
            except Exception as e:
                logger.warning(
                    f"Не удалось распарсить JSON: {str(e)}, возвращаем текст как есть"
                )
                # Создаем простой формат для отображения
                products = [
                    {"Наименование": text, "Количество": "", "Ед.изм.": ""}
                ]

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
