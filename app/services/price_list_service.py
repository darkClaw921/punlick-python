"""Сервис для работы с прайс-листами и векторной базой данных ChromaDB"""

import json
import uuid
import pandas as pd
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from tqdm import tqdm

from app.core.config import settings
from app.models.document import PriceListResponse


class PriceListService:
    """Сервис для работы с прайс-листами и векторной базой данных ChromaDB"""

    def __init__(self):
        """Инициализация сервиса и подключение к ChromaDB"""

        # Настройка логирования
        self.logger = logger.bind(context="price_list_service")
        self.log_file = "price_list_service.log"
        logger.add(
            self.log_file,
            encoding="utf-8",
            rotation="10MB",
            compression="zip",
            format="{time}|{file}:{line}|{level} {message}",
            level="INFO",
        )

        # Инициализация ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_DIR,
                settings=ChromaSettings(
                    allow_reset=True, anonymized_telemetry=False
                ),
            )

            # Получаем или создаем коллекцию
            try:
                self.collection = self.client.get_collection(
                    settings.CHROMA_COLLECTION_NAME
                )
                self.logger.info(
                    f"Коллекция {settings.CHROMA_COLLECTION_NAME} успешно подключена"
                )
            except:
                self.collection = self.client.create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={
                        "description": "Коллекция товаров из прайс-листов"
                    },
                )
                self.logger.info(
                    f"Коллекция {settings.CHROMA_COLLECTION_NAME} успешно создана"
                )

        except Exception as e:
            self.logger.error(f"Ошибка при инициализации ChromaDB: {str(e)}")
            raise Exception(f"Не удалось инициализировать ChromaDB: {str(e)}")

    async def process_price_list(
        self, file_path: str, original_filename: str
    ) -> PriceListResponse:
        """
        Обработка и загрузка прайс-листа в векторную базу данных

        Args:
            file_path: Путь к загруженному файлу прайс-листа
            original_filename: Оригинальное имя файла

        Returns:
            PriceListResponse: Информация о загруженном прайс-листе
        """
        try:
            # Генерируем уникальный ID для прайс-листа
            price_list_id = str(uuid.uuid4())

            # Читаем прайс-лист
            if file_path.endswith(".csv"):
                data = self._read_csv_price_list(file_path)
            elif file_path.endswith(".json"):
                data = self._read_json_price_list(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_path}")

            # Загружаем данные в ChromaDB
            total_items = self._load_data_to_chroma(data, price_list_id)

            # Подсчитываем количество категорий и подкатегорий
            categories_count = 0
            for category in data["categories"]:
                categories_count += 1
                for subcategory in data["categories"][category]:
                    categories_count += 1

            # Формируем ответ
            response = PriceListResponse(
                id=price_list_id,
                filename=original_filename,
                date=data["price_list_date"],
                currency=data["currency"],
                total_items=total_items,
                categories_count=categories_count,
                status="completed",
            )

            self.logger.info(
                f"Прайс-лист {original_filename} успешно обработан, "
                f"загружено {total_items} товаров из {categories_count} категорий"
            )

            return response

        except Exception as e:
            self.logger.error(
                f"Ошибка при обработке прайс-листа {original_filename}: {str(e)}"
            )
            raise Exception(f"Ошибка при обработке прайс-листа: {str(e)}")

    def _read_csv_price_list(self, file_path: str) -> Dict[str, Any]:
        """
        Чтение прайс-листа из CSV файла

        Args:
            file_path: Путь к CSV файлу

        Returns:
            Dict: Структурированные данные прайс-листа
        """
        try:
            # Чтение CSV файла с помощью pandas
            df = pd.read_csv(file_path, encoding="utf-8")

            # Проверка необходимых колонок
            required_columns = [
                "category",
                "subcategory",
                "article",
                "name",
                "price",
                "unit",
            ]
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(
                        f"В CSV файле отсутствует обязательная колонка: {col}"
                    )

            # Преобразование данных в нужный формат
            price_list_data = {
                "price_list_date": df.get("price_list_date", [None])[0]
                or "2023-01-01",
                "currency": df.get("currency", [None])[0] or "RUB",
                "categories": {},
            }

            # Группировка по категориям и подкатегориям
            for _, row in df.iterrows():
                category = row["category"]
                subcategory = row["subcategory"]

                if category not in price_list_data["categories"]:
                    price_list_data["categories"][category] = {}

                if subcategory not in price_list_data["categories"][category]:
                    price_list_data["categories"][category][subcategory] = []

                # Добавляем товар
                price_list_data["categories"][category][subcategory].append(
                    {
                        "article": row["article"],
                        "name": row["name"],
                        "price": float(row["price"]),
                        "unit": row["unit"],
                    }
                )

            return price_list_data

        except Exception as e:
            self.logger.error(f"Ошибка при чтении CSV файла: {str(e)}")
            raise Exception(f"Ошибка при чтении CSV файла: {str(e)}")

    def _read_json_price_list(self, file_path: str) -> Dict[str, Any]:
        """
        Чтение прайс-листа из JSON файла

        Args:
            file_path: Путь к JSON файлу

        Returns:
            Dict: Структурированные данные прайс-листа
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Проверка необходимых полей
            if "price_list_date" not in data:
                raise ValueError(
                    "В JSON файле отсутствует обязательное поле: price_list_date"
                )

            if "currency" not in data:
                raise ValueError(
                    "В JSON файле отсутствует обязательное поле: currency"
                )

            if "categories" not in data:
                raise ValueError(
                    "В JSON файле отсутствует обязательное поле: categories"
                )

            return data

        except Exception as e:
            self.logger.error(f"Ошибка при чтении JSON файла: {str(e)}")
            raise Exception(f"Ошибка при чтении JSON файла: {str(e)}")

    def _load_data_to_chroma(
        self, data: Dict[str, Any], price_list_id: str
    ) -> int:
        """
        Загрузка данных прайс-листа в ChromaDB

        Args:
            data: Структурированные данные прайс-листа
            price_list_id: Уникальный идентификатор прайс-листа

        Returns:
            int: Количество загруженных товаров
        """
        try:
            # Подготовка данных для векторизации
            ids = []
            documents = []
            metadatas = []

            # Обходим все категории и подкатегории
            total_items = 0

            for category_name, category_data in data["categories"].items():
                for subcategory_name, items in category_data.items():
                    for item in items:
                        # Генерируем уникальный ID для каждого товара
                        item_id = f"{price_list_id}_{category_name}_{subcategory_name}_{item['article']}"

                        # Текст для векторизации (название товара)
                        document = item["name"]

                        # Метаданные товара
                        metadata = {
                            "price_list_id": price_list_id,
                            "category": category_name,
                            "subcategory": subcategory_name,
                            "article": item["article"],
                            "price": float(item["price"]),
                            "unit": item.get("unit", ""),
                            "currency": data["currency"],
                            "price_list_date": data["price_list_date"],
                        }

                        ids.append(item_id)
                        documents.append(document)
                        metadatas.append(metadata)
                        total_items += 1

            # Загружаем данные пакетами по 1000 записей для экономии памяти
            batch_size = 1000
            for i in tqdm(
                range(0, len(ids), batch_size), desc="Загрузка в ChromaDB"
            ):
                batch_ids = ids[i : i + batch_size]
                batch_documents = documents[i : i + batch_size]
                batch_metadatas = metadatas[i : i + batch_size]

                self.collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                )

            self.logger.info(
                f"В ChromaDB успешно загружено {total_items} товаров из прайс-листа {price_list_id}"
            )
            return total_items

        except Exception as e:
            self.logger.error(
                f"Ошибка при загрузке данных в ChromaDB: {str(e)}"
            )
            raise Exception(f"Ошибка при загрузке данных в ChromaDB: {str(e)}")

    async def search_similar_items(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск похожих товаров в векторной базе данных

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            List[Dict]: Список найденных товаров
        """
        try:
            # Выполняем семантический поиск в ChromaDB
            results = self.collection.query(
                query_texts=[query], n_results=limit
            )

            # Форматируем результаты
            items = []
            if results and len(results["ids"]) > 0:
                for i, item_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]

                    items.append(
                        {
                            "id": item_id,
                            "article": metadata["article"],
                            "name": document,
                            "price": metadata["price"],
                            "unit": metadata["unit"],
                            "category": metadata["category"],
                            "subcategory": metadata["subcategory"],
                            "currency": metadata["currency"],
                            "price_list_date": metadata["price_list_date"],
                        }
                    )

            self.logger.info(
                f"Поиск по запросу '{query}' вернул {len(items)} результатов"
            )
            return items

        except Exception as e:
            self.logger.error(f"Ошибка при поиске товаров: {str(e)}")
            raise Exception(f"Ошибка при поиске товаров: {str(e)}")


# Экземпляр сервиса
price_list_service = PriceListService()
