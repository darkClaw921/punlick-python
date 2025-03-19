"""
Тестовый скрипт для проверки работы сервиса прайс-листов
"""

import os
import json
import asyncio
import sys
from pprint import pprint

import pandas as pd

# Добавляем корневую директорию в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.price_list_service import price_list_service


async def test_price_list_upload():
    """Тестирование загрузки прайс-листа"""

    # Путь к тестовому файлу
    test_file = "test_price_list2.csv"
    
    # Читаем JSON из CSV файла
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        
    # Выводим первые элементы для проверки
    print("Дата прайс-листа:", data["price_list_date"])
    print("Валюта:", data["currency"])
    print("\nПример товара:")
    first_category = next(iter(data["categories"]))
    first_subcategory = next(iter(data["categories"][first_category]))
    first_item = data["categories"][first_category][first_subcategory][0]
    pprint(first_item)
    1/0
    # Проверка существования файла
    if not os.path.exists(test_file):
        print(f"Файл {test_file} не найден. Создаем тестовый JSON...")

        # Создаем тестовый JSON-файл
        test_json_file = "test_price_list.json"

        # Пример данных
        test_data = {
            "price_list_date": "2023-01-01",
            "currency": "RUB",
            "categories": {
                "Воздуховоды": {
                    "Гофра вентиляционная": [
                        {
                            "article": "VTL-00154542",
                            "name": "Труба круглая гибкая гофрированная 2-х слойная d 110 (50 метров, серая), м",
                            "price": 304.8,
                            "unit": "м",
                        },
                        {
                            "article": "VTL-00159750",
                            "name": "Труба круглая гибкая гофрированная 2-х слойная d 90 (50 метров, салатовая), м",
                            "price": 251.46,
                            "unit": "м",
                        },
                    ],
                    "Неизолированный воздуховод": [
                        {
                            "article": "VTL-00000733",
                            "name": "Гибкий неизолированный воздуховод d 100 - 10 м, шт",
                            "price": 195,
                            "unit": "шт",
                        },
                        {
                            "article": "VTL-00000796",
                            "name": "Гибкий неизолированный воздуховод d 125 - 10 м, шт",
                            "price": 242,
                            "unit": "шт",
                        },
                    ],
                },
                "Водоснабжение": {
                    "Трубы металлопластиковые": [
                        {
                            "article": "VTL-00012345",
                            "name": "Труба металлопластиковая 16x2,0 мм, бухта 100 м",
                            "price": 52.5,
                            "unit": "м",
                        },
                        {
                            "article": "VTL-00012346",
                            "name": "Труба металлопластиковая 20x2,0 мм, бухта 100 м",
                            "price": 78.9,
                            "unit": "м",
                        },
                    ]
                },
            },
        }

        # Сохраняем в файл
        with open(test_json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        print(f"Тестовый файл {test_json_file} создан.")
        test_file = test_json_file

    # Загружаем прайс-лист
    try:
        result = await price_list_service.process_price_list(
            test_file, os.path.basename(test_file)
        )
        print("Прайс-лист успешно загружен:")
        pprint(result.dict())
        return True
    except Exception as e:
        print(f"Ошибка при загрузке прайс-листа: {str(e)}")
        return False


async def test_price_list_search():
    """Тестирование поиска в прайс-листе"""

    # Тестовые запросы для поиска
    test_queries = [
        "гофрированная труба",
        "воздуховод 100",
        "металлопластиковая труба",
        "изолированный воздуховод",
    ]

    for query in test_queries:
        try:
            print(f"\nПоиск по запросу: '{query}'")
            results = await price_list_service.search_similar_items(
                query, limit=5
            )

            if results:
                print(f"Найдено {len(results)} результатов:")
                for i, item in enumerate(results, 1):
                    print(
                        f"{i}. {item['name']} - {item['price']} {item['currency']}/{item['unit']}"
                    )
            else:
                print("Результатов не найдено.")
        except Exception as e:
            print(f"Ошибка при поиске: {str(e)}")


async def main():
    """Основная функция тестирования"""

    print("=== Тестирование сервиса прайс-листов ===")

    # Проверяем загрузку прайс-листа
    print("\n1. Тестирование загрузки прайс-листа")
    upload_success = await test_price_list_upload()

    # Если загрузка прошла успешно, проверяем поиск
    if upload_success:
        print("\n2. Тестирование поиска в прайс-листе")
        await test_price_list_search()

    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    asyncio.run(main())
