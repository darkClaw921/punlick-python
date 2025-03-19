"""
Фиксация структуры JSON и обработка как pandas DataFrame
"""

import pandas as pd
import os
import json
import re
from pprint import pprint

# Путь к файлу
file_path = "test_price_list2.csv"

# Проверка существования файла
if not os.path.exists(file_path):
    print(f"Файл {file_path} не найден.")
else:
    print(f"Обработка файла {file_path}...")
    
    # Чтение содержимого файла
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Исправление форматирования JSON...")
    
    # Удаляем внешние кавычки если они есть
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    
    # Заменяем двойные кавычки на одинарные
    content = content.replace('""', '"')
    
    # Исправляем общую структуру JSON - проблема с лишними закрывающими скобками и запятыми
    # Регулярное выражение для поиска проблемных мест: "],\n      ]}}}"
    content = re.sub(r'\],\s*\]\}\}\}"', ']}}', content)
    
    # Удаляем висячие запятые в конце массивов JSON (перед закрывающей ])
    content = re.sub(r',(\s*\])', r'\1', content)
    
    # Исправляем обрезанные числа (например 251. -> 251.0)
    content = re.sub(r'(\d+)\.,', r'\1.0,', content)
    content = re.sub(r'(\d+)\."', r'\1.0"', content)
    content = re.sub(r'(\d+)\.\s', r'\1.0 ', content)
    content = re.sub(r'(\d+)\.$', r'\1.0', content)
    
    # Сохраняем исправленный JSON во временный файл
    fixed_json_file = "fixed_price_list.json"
    with open(fixed_json_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Исправленный JSON сохранен в {fixed_json_file}")
    
    try:
        # Пробуем загрузить исправленный JSON
        with open(fixed_json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                print("JSON успешно загружен")
                
                # Выводим базовую информацию о данных
                print(f"Дата прайс-листа: {data.get('price_list_date')}")
                print(f"Валюта: {data.get('currency')}")
                
                # Преобразуем данные в плоский список для создания DataFrame
                flat_data = []
                
                for category_name, subcategories in data.get('categories', {}).items():
                    # Проверяем, является ли subcategories словарем
                    if isinstance(subcategories, dict):
                        for subcategory_name, items in subcategories.items():
                            # Проверяем, является ли items списком
                            if isinstance(items, list):
                                for item in items:
                                    if isinstance(item, dict):
                                        item_data = {
                                            'категория': category_name,
                                            'подкатегория': subcategory_name,
                                            'артикул': item.get('article', ''),
                                            'наименование': item.get('name', ''),
                                            'цена': item.get('price', 0),
                                            'единица': item.get('unit', '')
                                        }
                                        flat_data.append(item_data)
                
                # Создаем DataFrame
                df = pd.DataFrame(flat_data)
                
                # Выводим информацию о DataFrame
                print("\nИнформация о DataFrame:")
                print(f"Размер: {df.shape[0]} строк, {df.shape[1]} столбцов")
                print("\nПервые 5 строк:")
                print(df.head())
                
                # Выводим статистику
                print("\nСтатистика по ценам:")
                print(df['цена'].describe())
                
                # Сохраняем в CSV
                output_csv = "processed_price_list.csv"
                df.to_csv(output_csv, index=False, encoding='utf-8')
                print(f"\nДанные сохранены в {output_csv}")
                
            except json.JSONDecodeError as e:
                print(f"Ошибка при разборе JSON: {str(e)}")
                print(f"Проверьте исправленный файл {fixed_json_file} вручную")
    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")

print("Обработка завершена.") 