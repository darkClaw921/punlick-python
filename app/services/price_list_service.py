"""Сервис для работы с прайс-листами и векторной базой данных ChromaDB"""
import re
# from price_validator_service import PriceValidatorService
from pprint import pprint
import json
import traceback
import uuid
import pandas as pd
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from tqdm import tqdm
import os
from mistralai import Mistral
from datetime import datetime

from app.core.config import settings
from app.models.document import PriceListResponse


class PriceListService:
    """Сервис для работы с прайс-листами и векторной базой данных ChromaDB"""

    def __init__(self):
        """Инициализация сервиса и подключение к ChromaDB"""
        # Настраиваем логгер
        self.logger = logger.bind(context="price_list_service")

        # Создаем директорию для векторной БД, если не существует
        os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)

        # Загружаем API ключ Mistral из переменных окружения
        self.mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        self.mistral_client = None

        # Пытаемся инициализировать Mistral API клиент
        if self.mistral_api_key:
            try:
                self.mistral_client = Mistral(api_key=self.mistral_api_key)
                self.mistral_model = "mistral-embed"  # Добавляем модель по умолчанию
                self.logger.info("Mistral API клиент успешно инициализирован")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать Mistral API клиент: {str(e)}")
        else:
            self.logger.warning("MISTRAL_API_KEY не найден в переменных окружения. Будет использована встроенная модель эмбеддингов.")

        # Словарь для хранения статусов загрузки
        self.upload_statuses = {}

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
                # Если используем Mistral для эмбеддингов, указываем это при создании коллекции
                if self.mistral_client:
                    self.collection = self.client.create_collection(
                        name=settings.CHROMA_COLLECTION_NAME,
                        metadata={
                            "description": "Коллекция товаров из прайс-листов",
                            "embedding_model": "mistral-embed"
                        },
                    )
                else:
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

            # Читаем прайс-лист в зависимости от формата
            if file_path.endswith(".csv"):
                data = self._read_csv_price_list(file_path)
            elif file_path.endswith(".json"):
                data = self._read_json_price_list(file_path)
            elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                data = self._read_excel_price_list(file_path)
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

    async def _read_excel_price_list(self, file_path: str) -> Dict[str, Any]:
        """
        Чтение прайс-листа из Excel файла, пропуская первые 5 строк заголовка
        Специально для формата прайс-листа с воздуховодами и объединенными ячейками

        Args:
            file_path: Путь к Excel файлу

        Returns:
            Dict: Структурированные данные прайс-листа
        """
        try:
            # Попытка определить дату из имени файла или содержимого
            price_list_date = pd.Timestamp.now().strftime("%Y-%m-%d")
            try:
                # Чтение первых строк для поиска даты
                header_df = pd.read_excel(file_path, header=None, nrows=5)
                # Ищем строку с датой (обычно в первой строке первый столбец содержит "Прайс-лист на")
                for i in range(5):
                    for j in range(3):  # Проверяем первые 3 столбца
                        cell_value = str(header_df.iloc[i, j]).strip() if not pd.isna(header_df.iloc[i, j]) else ""
                        if "прайс-лист на" in cell_value.lower():
                            # Извлекаем дату из строки
                            date_parts = cell_value.split("на")[-1].strip().split()
                            if len(date_parts) >= 3:
                                # Конвертируем месяц в числовой формат
                                month_map = {
                                    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
                                    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
                                    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
                                }
                                day = date_parts[0]
                                month = month_map.get(date_parts[1].lower(), "01")
                                year = date_parts[2].replace("г.", "").strip()
                                price_list_date = f"{year}-{month}-{day}"
                                break
            except Exception as e:
                self.logger.warning(f"Не удалось извлечь дату из заголовка прайс-листа: {str(e)}")

            # Чтение Excel файла, пропуская первые 5 строк для заголовков
            df = pd.read_excel(file_path, header=5)

            # Переименуем столбцы для лучшего понимания
            # Предполагаем, что первая колонка содержит наименование
            # а последние две колонки - цену и валюту
            column_names = {}
            for i, col in enumerate(df.columns):
                if i == 0:
                    column_names[col] = 'Наименование'
                elif i == len(df.columns) - 2:
                    column_names[col] = 'Цена'
                elif i == len(df.columns) - 1:
                    column_names[col] = 'Валюта'
                else:
                    # Ищем колонку с описанием (обычно колонка с наибольшим количеством текста)
                    non_null_values = df[col].dropna()
                    if len(non_null_values) > 0 and isinstance(non_null_values.iloc[0], str) and len(non_null_values.iloc[0]) > 10:
                        column_names[col] = 'Описание'

            df.rename(columns=column_names, inplace=True)

            # Определяем валюту
            currency = "RUB"  # По умолчанию рубли
            if 'Валюта' in df.columns:
                currencies = df['Валюта'].dropna().unique()
                if len(currencies) > 0:
                    currency = str(currencies[0])

            # Обработка иерархической структуры
            df['Категория'] = None
            df['Подкатегория'] = None
            current_category = None
            current_subcategory = None

            for i, row in df.iterrows():
                name = row.get('Наименование', '')
                price = row.get('Цена', None)
                
                # Проверяем наличие значений
                if pd.isna(name):
                    continue
                    
                name = str(name).strip()
                    
                # Если строка без цены и не содержит артикул (не начинается с 'VTL-'), 
                # то это категория или подкатегория
                if (pd.isna(price) or price == 0) and not name.startswith('VTL-'):
                    if current_category is None or "воздуховоды" in name.lower():
                        current_category = name
                        current_subcategory = None
                    else:
                        current_subcategory = name
                
                df.at[i, 'Категория'] = current_category
                df.at[i, 'Подкатегория'] = current_subcategory

            # Отфильтруем только строки с товарами (имеющие цену)
            products_df = df.dropna(subset=['Цена']).copy()
            products_df = products_df[products_df['Цена'] > 0].copy()

            # Формируем структуру прайс-листа
            price_list_data = {
                "price_list_date": price_list_date,
                "currency": currency,
                "categories": {}
            }

            # Группировка по категориям и подкатегориям
            for _, row in products_df.iterrows():
                category = row.get('Категория')
                subcategory = row.get('Подкатегория')
                
                if pd.isna(category) or category is None:
                    category = "Неизвестная категория"
                    
                if pd.isna(subcategory) or subcategory is None:
                    subcategory = "Неизвестная подкатегория"
                
                if category not in price_list_data["categories"]:
                    price_list_data["categories"][category] = {}

                if subcategory not in price_list_data["categories"][category]:
                    price_list_data["categories"][category][subcategory] = []

                # Получаем артикул из наименования
                article = row.get('Наименование', '')
                name = article  # По умолчанию
                
                # Выделяем описание
                description = str(row.get('Описание', '')) if not pd.isna(row.get('Описание', '')) else ""
                
                # Если нет описания, но есть длинное наименование, попробуем выделить описание из наименования
                if not description and len(str(article)) > 20:
                    # Предполагаем, что артикул в формате "VTL-XXXXXXXX" и идет в начале
                    parts = str(article).split(" ", 1)
                    if len(parts) > 1 and parts[0].startswith("VTL-"):
                        article = parts[0]
                        description = parts[1]
                        name = parts[0]  # VTL-код как наименование
                
                # Добавляем товар
                price_list_data["categories"][category][subcategory].append({
                    "article": article,
                    "name": name,
                    "description": description,
                    "price": float(row.get('Цена')),
                    "unit": "шт",  # По умолчанию используем "шт"
                })

            self.logger.info(f"Excel прайс-лист успешно прочитан, найдено {len(products_df)} товаров с ценами")
            return price_list_data

        except Exception as e:
            self.logger.error(f"Ошибка при чтении Excel файла: {str(e)}")
            raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")

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

                        # Текст для векторизации (название товара и описание)
                        description = item.get("description", "")
                        document = f"{description}".strip()

                        # Метаданные товара
                        metadata = {
                            "price_list_id": price_list_id,
                            "category": category_name,
                            "subcategory": subcategory_name,
                            "article": item["article"],
                            "name": item["name"],
                            "description": description,
                            "price": float(item["price"]),
                            "unit": item.get("unit", ""),
                            "currency": data["currency"],
                            "price_list_date": data["price_list_date"],
                        }

                        ids.append(item_id)
                        documents.append(document)
                        metadatas.append(metadata)
                        total_items += 1

            # Получаем эмбеддинги через Mistral API
            embeddings = None
            if self.mistral_client:
                self.logger.info(f"Получение эмбеддингов через Mistral API для {len(documents)} документов")
                embeddings = self._get_embeddings(documents)
                if embeddings:
                    self.logger.info(f"Получены эмбеддинги через Mistral API: {len(embeddings)} векторов")

            # Загружаем данные пакетами по 1000 записей для экономии памяти
            batch_size = 1000
            for i in tqdm(
                range(0, len(ids), batch_size), desc="Загрузка в ChromaDB"
            ):
                batch_ids = ids[i : i + batch_size]
                batch_documents = documents[i : i + batch_size]
                batch_metadatas = metadatas[i : i + batch_size]
                
                # Используем эмбеддинги Mistral, если они доступны
                if embeddings:
                    batch_embeddings = embeddings[i : i + batch_size]
                    self.collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas,
                        embeddings=batch_embeddings
                    )
                else:
                    # Если эмбеддинги Mistral недоступны, используем встроенные эмбеддинги ChromaDB
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
        self, 
        query: str, 
        limit: int = 10,
        supplier_id: str = None,
        min_price: float = None,
        max_price: float = None,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск похожих товаров в векторной базе данных с возможностью фильтрации

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            supplier_id: Фильтрация по ID поставщика
            min_price: Минимальная цена для фильтрации результатов
            max_price: Максимальная цена для фильтрации результатов
            category: Фильтрация по категории

        Returns:
            List[Dict]: Список найденных товаров
        """
        try:
            # Подготавливаем фильтрацию по метаданным
            where_filter = {}
            
            if supplier_id:
                where_filter["supplier_id"] = supplier_id
                
            if category:
                where_filter["category"] = category
            
            # Определяем количество результатов с запасом для фильтрации по цене
            search_limit = limit * 3 if (min_price is not None or max_price is not None) else limit
            
            # Получаем эмбеддинг запроса через Mistral, если доступно
            query_embedding = None
            if self.mistral_client:
                try:
                    self.logger.info(f"Получение эмбеддинга для поискового запроса: '{query}'")
                    embeddings_response = await self.mistral_client.embeddings.create_async(
                        model="mistral-embed",
                        inputs=[query]
                    )
                    query_embedding = embeddings_response.data[0].embedding
                    self.logger.info(f"Получен эмбеддинг запроса размером {len(query_embedding)}")
                except Exception as e:
                    self.logger.error(f"Ошибка при получении эмбеддинга запроса: {str(e)}")
                    query_embedding = None
            
            # Выполняем семантический поиск в ChromaDB
            if where_filter:
                # Поиск с фильтрацией
                if query_embedding:
                    # Если есть эмбеддинг запроса от Mistral, используем его
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=search_limit,
                        where=where_filter
                    )
                else:
                    # Иначе используем текстовый запрос
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=search_limit,
                        where=where_filter
                    )
            else:
                # Поиск без фильтрации
                if query_embedding:
                    # Если есть эмбеддинг запроса от Mistral, используем его
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=search_limit
                    )
                else:
                    # Иначе используем текстовый запрос
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=search_limit
                    )

            # Форматируем результаты
            items = []
            if results and len(results["ids"]) > 0:
                for i, item_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    
                    # Применяем фильтрацию по цене, если указана
                    price = float(metadata["price"])
                    if (min_price is not None and price < min_price) or (max_price is not None and price > max_price):
                        continue
                    
                    # Получаем расстояние между запросом и результатом (релевантность)
                    relevance = results.get("distances", [[]])[0][i] if "distances" in results else None
                    
                    items.append(
                        {
                            "id": item_id,
                            "article": metadata["article"],
                            "name": metadata["name"],
                            "description": metadata.get("description", ""),
                            "price": price,
                            "unit": metadata["unit"],
                            "category": metadata["category"],
                            "subcategory": metadata["subcategory"],
                            "currency": metadata["currency"],
                            "price_list_date": metadata.get("price_list_date", pd.Timestamp.now().strftime("%Y-%m-%d")),
                            "supplier_id": metadata.get("supplier_id", ""),
                            "relevance": 1.0 - relevance if relevance is not None else None  # Преобразуем расстояние в релевантность
                        }
                    )
                    
                    # Если достигли лимита после фильтрации, прерываем обработку
                    if len(items) >= limit:
                        break

            self.logger.info(
                f"Поиск по запросу '{query}' вернул {len(items)} результатов " +
                (f"от поставщика {supplier_id}" if supplier_id else "") +
                (f" в ценовом диапазоне {min_price}-{max_price}" if min_price is not None or max_price is not None else "")
            )
            return items

        except Exception as e:
            self.logger.error(f"Ошибка при поиске товаров: {traceback.format_exc()}")
            raise Exception(f"Ошибка при поиске товаров: {str(e)}")

    async def update_price_list_collection(
        self, 
        file_path: str, 
        original_filename: str, 
        replace_existing: bool = False,
        clear_by_supplier: bool = False,
        supplier_id: str = None
    ) -> PriceListResponse:
        """
        Обновление коллекции товаров в ChromaDB из прайс-листа
        
        Args:
            file_path: Путь к загруженному файлу прайс-листа
            original_filename: Оригинальное имя файла
            replace_existing: Заменить все существующие товары (True) или добавить новые (False)
            clear_by_supplier: Удалить только товары конкретного поставщика перед обновлением
            supplier_id: ID поставщика, товары которого нужно удалить (работает только если clear_by_supplier=True)
            
        Returns:
            PriceListResponse: Информация о загруженном прайс-листе
        """
        try:
            # Генерируем уникальный ID для прайс-листа
            price_list_id = str(uuid.uuid4())
            
            # Инициализируем статус загрузки
            self._update_upload_status(
                upload_id=price_list_id,
                status="processing",
                percent_complete=0,
                current_stage="Подготовка к обработке"
            )
            
            # Определяем ID поставщика, если не указан
            if supplier_id is None:
                # Если не указан, пытаемся определить из имени файла или используем ID прайс-листа
                supplier_id = original_filename.split('.')[0] if '.' in original_filename else price_list_id
            
            # Если необходимо заменить существующие данные
            if replace_existing:
                self._update_upload_status(
                    upload_id=price_list_id,
                    status="processing",
                    percent_complete=5,
                    current_stage="Очистка существующей коллекции"
                )
                
                # Проверяем наличие коллекции и удаляем ее, если она существует
                try:
                    self.client.delete_collection(settings.CHROMA_COLLECTION_NAME)
                    self.logger.info(f"Коллекция {settings.CHROMA_COLLECTION_NAME} успешно удалена")
                except Exception as e:
                    self.logger.info(f"Коллекция {settings.CHROMA_COLLECTION_NAME} не существует или не может быть удалена: {str(e)}")
                
                # Создаем новую коллекцию
                self.collection = self.client.create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={"description": "Коллекция товаров из прайс-листов"},
                )
                self.logger.info(f"Коллекция {settings.CHROMA_COLLECTION_NAME} успешно создана")
            
            # Если необходимо удалить товары конкретного поставщика
            elif clear_by_supplier and supplier_id:
                self._update_upload_status(
                    upload_id=price_list_id,
                    status="processing",
                    percent_complete=5,
                    current_stage=f"Удаление товаров поставщика {supplier_id}"
                )
                
                try:
                    # Получаем список товаров данного поставщика
                    results = self.collection.get(
                        where={"supplier_id": supplier_id}
                    )
                    
                    if results and "ids" in results and len(results["ids"]) > 0:
                        # Удаляем товары поставщика
                        self.collection.delete(
                            ids=results["ids"]
                        )
                        self.logger.info(f"Удалено {len(results['ids'])} товаров поставщика {supplier_id}")
                except Exception as e:
                    self.logger.warning(f"Не удалось удалить существующие товары поставщика {supplier_id}: {str(e)}")

            # Обновляем статус - чтение файла
            self._update_upload_status(
                upload_id=price_list_id,
                status="processing",
                percent_complete=10,
                current_stage="Чтение прайс-листа"
            )

            # Читаем прайс-лист в зависимости от формата
            if file_path.endswith(".csv"):
                data = self._read_csv_price_list(file_path)
            elif file_path.endswith(".json"):
                data = self._read_json_price_list(file_path)
            elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                data = await self._read_excel_price_list(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_path}")
            
            # Подсчитываем количество товаров для статуса
            total_items_count = 0
            for category in data["categories"]:
                for subcategory in data["categories"][category]:
                    total_items_count += len(data["categories"][category][subcategory])
            
            self._update_upload_status(
                upload_id=price_list_id,
                status="processing",
                percent_complete=30,
                current_stage="Загрузка товаров в базу данных",
                total_items=total_items_count
            )
            
            # Добавляем информацию о поставщике
            data["supplier_id"] = supplier_id
            
            # Загружаем данные в ChromaDB с учетом поставщика и обновлением статуса
            total_items = await self._load_data_to_chroma_with_supplier(data, price_list_id, supplier_id, price_list_id)

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
                supplier_id=supplier_id
            )

            # Обновляем статус - завершено
            self._update_upload_status(
                upload_id=price_list_id,
                status="completed",
                percent_complete=100,
                processed_items=total_items,
                total_items=total_items,
                current_stage="Загрузка завершена",
                result=response.dict()
            )

            operation_type = "заменена вся база" if replace_existing else f"обновлены товары {supplier_id}" if clear_by_supplier else "добавлены товары"
            self.logger.info(
                f"Прайс-лист {original_filename} успешно обработан ({operation_type}), "
                f"загружено {total_items} товаров из {categories_count} категорий"
            )

            return response

        except Exception as e:
            # Обновляем статус - ошибка
            self._update_upload_status(
                upload_id=price_list_id if 'price_list_id' in locals() else str(uuid.uuid4()),
                status="error",
                percent_complete=0,
                current_stage="Ошибка обработки",
                error=str(e)
            )
            
            self.logger.error(
                f"Ошибка при обновлении коллекции из прайс-листа {original_filename}: {str(e)}"
            )
            raise Exception(f"Ошибка при обновлении коллекции: {str(e)}")
            
    async def _load_data_to_chroma_with_supplier(
        self, data: Dict[str, Any], price_list_id: str, supplier_id: str, upload_id: str = None
    ) -> int:
        """
        Загрузка данных из прайс-листа в ChromaDB с учетом поставщика
        
        Args:
            data: Данные прайс-листа
            price_list_id: ID прайс-листа
            supplier_id: ID поставщика
            upload_id: ID процесса загрузки для обновления статуса
            
        Returns:
            int: Количество загруженных товаров
        """
        try:
            # Подготовка данных
            ids = []
            documents = []
            metadatas = []
            total_items = 0
            
            # Проходим по всем категориям и подкатегориям
            for category, subcategories in data["categories"].items():
                for subcategory, items in subcategories.items():
                    # Проходим по всем товарам
                    for item in items:
                        # Формируем уникальный ID для товара на основе артикула или имени
                        item_id = f"{supplier_id}_{item.get('article', '').replace(' ', '_') or (item.get('name', '')[:20]).replace(' ', '_')}_{total_items}"
                        
                        # Формируем документ для поиска (объединяем всю информацию о товаре)
                        document = f"{item.get('description', '')}"
                        
                        # Формируем метаданные товара
                        metadata = {
                            "article": item.get("article", ""),
                            "name": item.get("name", ""),
                            "price": item.get("price", 0),
                            "unit": item.get("unit", ""),
                            "description": item.get("description", ""),
                            "category": category,
                            "subcategory": subcategory,
                            "price_list_id": price_list_id,
                            "supplier_id": supplier_id,
                            "currency": data.get("currency", "RUB"),
                            "price_list_date": data.get("price_list_date", pd.Timestamp.now().strftime("%Y-%m-%d")),
                        }
                        
                        # Добавляем информацию в списки
                        ids.append(item_id)
                        documents.append(document)
                        metadatas.append(metadata)
                        
                        total_items += 1
            
            # Получаем эмбеддинги через Mistral API, если возможно
            embeddings = None
            if self.mistral_client:
                if upload_id:
                    self._update_upload_status(
                        upload_id=upload_id,
                        status="processing",
                        percent_complete=40,
                        processed_items=0,
                        total_items=total_items,
                        current_stage="Получение эмбеддингов через Mistral API"
                    )
                embeddings = await self._get_embeddings(documents)

            # Загружаем данные пакетами по 1000 записей для экономии памяти
            batch_size = 1000
            for i, batch_start in enumerate(tqdm(
                range(0, len(ids), batch_size), desc="Загрузка в ChromaDB"
            )):
                batch_end = min(batch_start + batch_size, len(ids))
                batch_ids = ids[batch_start:batch_end]
                batch_documents = documents[batch_start:batch_end]
                batch_metadatas = metadatas[batch_start:batch_end]
                
                # Обновляем статус загрузки, если есть upload_id
                if upload_id:
                    progress_percent = 40 + (i * batch_size / total_items) * 60
                    self._update_upload_status(
                        upload_id=upload_id,
                        status="processing",
                        percent_complete=progress_percent,
                        processed_items=min(i * batch_size, total_items),
                        total_items=total_items,
                        current_stage="Загрузка в векторную базу данных"
                    )
                
                # Используем эмбеддинги Mistral, если они доступны
                if embeddings:
                    batch_embeddings = embeddings[batch_start:batch_end]
                    self.collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas,
                        embeddings=batch_embeddings
                    )
                else:
                    # Если эмбеддинги Mistral недоступны, используем встроенные эмбеддинги ChromaDB
                    self.collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas,
                    )

            self.logger.info(
                f"В ChromaDB успешно загружено {total_items} товаров из прайс-листа {price_list_id} от поставщика {supplier_id}"
            )
            return total_items

        except Exception as e:
            # Обновляем статус при ошибке
            if upload_id:
                self._update_upload_status(
                    upload_id=upload_id,
                    status="error",
                    current_stage="Ошибка при загрузке данных",
                    error=str(e)
                )
            
            self.logger.error(
                f"Ошибка при загрузке данных в ChromaDB: {str(e)}"
            )
            raise Exception(f"Ошибка при загрузке данных в ChromaDB: {str(e)}")
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
            print(f"Ошибка извлечения списка: {str(e)}")
            return None
        
    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получение эмбеддингов для текстов с использованием Mistral API
        
        Args:
            texts: Список текстов для векторизации
            
        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        if not self.mistral_client:
            return None  # Вернем None, чтобы ChromaDB использовал свои встроенные эмбеддинги
            
        try:
            # Разделим запросы на части по 20 текстов для оптимизации API запросов
            batch_size = 100
            all_embeddings = []
            
            for i in tqdm(range(0, len(texts), batch_size), desc="Получение эмбеддингов"):
                batch_texts = texts[i:i+batch_size]
                try:
                    response = await self.mistral_client.embeddings.create_async(
                        model="mistral-embed",
                        inputs=batch_texts
                    )
                    
                    # Извлекаем эмбеддинги из ответа
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при получении эмбеддингов через Mistral API: {str(e)}")
                    return None  # Вернем None, чтобы ChromaDB использовал свои встроенные эмбеддинги
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении эмбеддингов через Mistral API: {str(e)}")
            return None  # Вернем None, чтобы ChromaDB использовал свои встроенные эмбеддинги

    # Метод для получения статуса загрузки
    def get_upload_status(self, upload_id: str) -> Dict[str, Any]:
        """
        Получение статуса загрузки прайс-листа по ID
        
        Args:
            upload_id: ID процесса загрузки
            
        Returns:
            Dict: Информация о статусе загрузки
        """
        if upload_id in self.upload_statuses:
            return self.upload_statuses[upload_id]
        return None

    # Метод для обновления статуса загрузки
    def _update_upload_status(
        self, 
        upload_id: str, 
        status: str = "processing", 
        percent_complete: float = 0, 
        processed_items: int = 0, 
        total_items: int = 0,
        current_stage: str = None,
        result: Dict[str, Any] = None,
        error: str = None
    ):
        """
        Обновление статуса загрузки прайс-листа
        
        Args:
            upload_id: ID процесса загрузки
            status: Статус загрузки (processing, completed, error)
            percent_complete: Процент выполнения (0-100)
            processed_items: Количество обработанных товаров
            total_items: Общее количество товаров
            current_stage: Текущий этап обработки
            result: Результат обработки (при status=completed)
            error: Ошибка (при status=error)
        """
        self.upload_statuses[upload_id] = {
            "status": status,
            "percent_complete": percent_complete,
            "processed_items": processed_items,
            "total_items": total_items,
            "current_stage": current_stage,
            "result": result,
            "error": error,
            "updated_at": datetime.now().isoformat()
        }



    @logger.catch
    async def find_matching_items(self, items: List[Dict[str, Any]], similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Поиск соответствий распознанных товаров в векторной базе и замена названий на эталонные
        
        Args:
            items: Список распознанных товаров
            similarity_threshold: Минимальный порог сходства для замены (0.0-1.0)
            
        Returns:
            List[Dict]: Список обогащенных товаров с эталонными названиями
        """
        from chromaWork import ChromaWork
        try:
            chromaDB = ChromaWork('test')
            # Результирующий список
            enriched_items = []
            
            self.logger.info(f"Начало поиска соответствий для {len(items)} товаров с порогом {similarity_threshold * 100}%")
            
            for idx, item in enumerate(items):
                # Получаем название товара
                print(item)

                item_name = item.get("Наименование", "")
                # item_name = item.text
                    
                # Если имя товара не пустое, ищем совпадения в базе
                if item_name:
                    self.logger.info(f"[Товар {idx+1}] Поиск соответствий для: '{item_name}'")
                    # item_name = item_name.replace("Φ", "d")
                    # item_name = item_name.replace("Ф", "d")
                    # Ищем похожие товары в векторной базе
                    promt = chromaDB.get_items(item_name, isReturnPromt=True)

                    response = await self.mistral_client.chat.complete_async(
                        model="mistral-small-latest",
                        messages=[
                            {"role": "system", "content": f"вот правила для правильного наименования{promt}"},
                            {"role": "user", "content": f"верни правильное наименование для: {item_name} в формате json список с полями 'Наименование', 'Ед.изм.', 'Количество'"}
                            # {"role": "system", "content": f"Ты помощник для поиска соответствий в базе данных. Ты должен найти соответствие для запроса среди списка текстов. Если соответствие найдено, верни его в формате json с полями 'Наименование', 'Ед.изм.', 'Количество'. Если соответствие не найдено, верни null. и учти что Ф это d. Вот еще правила  {promt}"},
                            # {"role": "user", "content": f"Найди соответствие для: {item_name} среди: {allTexts}"}
                        ],
                        max_tokens=40000
                    )
                    # pprint(response)
                    answer = self.prepare_text_anserw_to_dict(response.choices[0].message.content)
                    print("Правильное наименование: ", answer)

                    try:
                        answerName = answer[0]["Наименование"]
                    except:
                        continue

                    matches = await self.search_similar_items(query=answerName, limit=5)
                        

                    # pprint(matches)
                    allTexts = [match["description"] for match in matches]
                    
                    allTexts = '\n'.join(allTexts)
                    print("Список похожих товаров из базы данных: ", allTexts)
                    response = await self.mistral_client.chat.complete_async(
                        model="mistral-small-latest",
                        messages=[
                            {"role": "system", "content": f"вот список товаров из базы данных {allTexts}"},
                            {"role": "user", "content": f"верни то что больше соответствует: {item_name} в формате json список с полями 'Наименование', 'Ед.изм.', 'Количество'"}
                            # {"role": "system", "content": f"Ты помощник для поиска соответствий в базе данных. Ты должен найти соответствие для запроса среди списка текстов. Если соответствие найдено, верни его в формате json с полями 'Наименование', 'Ед.изм.', 'Количество'. Если соответствие не найдено, верни null. и учти что Ф это d. Вот еще правила  {promt}"},
                            # {"role": "user", "content": f"Найди соответствие для: {item_name} среди: {allTexts}"}
                        ],
                        max_tokens=40000,
                        temperature=0.9
                    )
                    # print("===================\n", allTexts)
                    answer = self.prepare_text_anserw_to_dict(response.choices[0].message.content)
                    print("более подходящий товар: для ", item_name, answer)

                    enriched_items.append(answer[0])
                    
            
            
            pprint(enriched_items)
            return enriched_items
            
        except Exception as e:
            self.logger.error(f"{traceback.format_exc()}")
            self.logger.error(f"Ошибка при поиске соответствий товаров: {str(e)}")
            # В случае ошибки возвращаем исходный список
            return items

# Экземпляр сервиса
price_list_service = PriceListService()
#uv run app:/services/price_list_service.py 
if __name__ == "__main__":
    import asyncio
    from pprint import pprint
    # price_list_service = PriceListService()
    # asyncio.run(price_list_service.update_price_list_collection(file_path="/Users/igorgerasimov/Downloads/наш прайс воздуховодов2.xlsx", 
                                                                # original_filename="наш прайс воздуховодов2.xlsx", ))
    items = [
   
    {
        "Наименование": "Врезка Φ125/Φ200",
        "Количество": "1",
        "Ед.изм.": "шт"
    },
    
    {
        "Наименование": "Переход Φ315/Φ250",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
   
    {
        "Наименование": "Узел прохода УП-1 (без клапана) d 125 -1250",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    
]
    price_list_service = PriceListService()
    finds = asyncio.run(price_list_service.find_matching_items(items))
    pprint(finds)
    
    # validator = PriceValidatorService()
    # validated = asyncio.run(validator.validate_and_correct_items(finds))
    # pprint(validated)

    #заполнение базы данных
                                                            #  original_filename="наш прайс воздуховодов2.xlsx", 
                                                                
                                                                # ))