import json
import re
import pandas as pd
from typing import Optional
from loguru import logger
from mistralai import Mistral
from tqdm import tqdm

from app.core.config import settings
from app.models.document import DocumentResponse, DocumentItem
from app.services.price_list_service import PriceListService

logger.add(
    "xlsx_service.log",
    encoding="utf-8",
    rotation="10MB",
    compression="zip",
    format="{time}|{file}:{line}|{level} {message}",
    level="INFO",
)


class XLSXService:
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

    async def process_xlsx_file(
        self, file_path: str, original_filename: str
    ) -> DocumentResponse:
        """Обработка XLSX файла с использованием Mistral API"""
        try:
            logger.debug(f"Обработка XLSX файла: {original_filename}")

            # Чтение данных из XLSX файла
            try:
                df = pd.read_excel(file_path)
                # Преобразование DataFrame в текстовый формат
                xlsx_content = df.to_string(index=False)
                logger.debug("Содержимое XLSX файла преобразовано в текст")
            except Exception as e:
                logger.error(f"Ошибка при чтении XLSX файла: {str(e)}")
                raise ValueError(f"Не удалось прочитать XLSX файл: {str(e)}")
            xlsx_content=xlsx_content.replace('NaN', '')
            logger.debug(f"Содержимое XLSX файла: {xlsx_content}")

            # Разбиваем содержимое на батчи по 50 строк
            
            lines = xlsx_content.split('\n')
            batch_size = 50
            batches = ['\n'.join(lines[i:i+batch_size]) for i in range(0, len(lines), batch_size)]
            logger.debug(f"Файл разбит на {len(batches)} батчей по {batch_size} строк")
            

            all_products = []
            for batch in tqdm(batches, desc="Обработка батчей XLSX"):
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """найди все товары и верни их в виде списка в формате json с полями "Наименование":"наименование товара","Количество":"количество товара","Ед.изм.":"единица измерения товара" """,
                            },
                            {"type": "text", "text": batch},
                        ],
                    }
                ]

                # Получаем ответ от API
                chat_response = await self._client.chat.complete_async(
                    model="mistral-large-latest", messages=messages, max_tokens=40000
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

                all_products.extend(products)

            # Создаем уникальный ID для файла
            file_id = f"xlsx_{original_filename}"

            # document_response = DocumentResponse(
            #     id=file_id,
            #     original_filename=original_filename,
            #     items=[
            #         DocumentItem(
            #             text=item
            #             if isinstance(item, str)
            #             else json.dumps(item, ensure_ascii=False)
            #         )
            #         for item in all_products
            #     ],
            # )
            price_list_service = PriceListService()
            enriched_products = await price_list_service.find_matching_items(all_products)

            document_response = DocumentResponse(
                id=file_id,
                original_filename=original_filename,
                items=[
                    DocumentItem(
                        text=item
                        if isinstance(item, str)
                        else json.dumps(item, ensure_ascii=False)
                    )
                    for item in enriched_products
                ],
            )

            # Сохранение результата
            self._results[file_id] = document_response

            return document_response
            # Сохранение результата
            # self._results[file_id] = document_response

            # return document_response

        except Exception as e:
            logger.error(
                f"Ошибка при обработке XLSX файла {original_filename}: {str(e)}"
            )
            raise

    def get_result(self, file_id: str) -> Optional[DocumentResponse]:
        """Получение результата обработки по ID файла"""
        return self._results.get(file_id)


# Создание экземпляра сервиса
xlsx_service = XLSXService()
