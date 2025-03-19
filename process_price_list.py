"""
Обработка прайс-листа CSV: замена двойных кавычек на одинарные и преобразование в pandas DataFrame
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
    
    # Замена двойных кавычек на одинарные в JSON строке
    content_fixed = content.replace('""', '"')
    
    # Удаляем первую и последнюю кавычку, если они есть
    if content_fixed.startswith('"') and content_fixed.endswith('"'):
        content_fixed = content_fixed[1:-1]
    
    # Исправляем обрезанные числа (например, 251. -> 251.0)
    content_fixed = re.sub(r'(\d+)\.,', r'\1.0,', content_fixed)
    content_fixed = re.sub(r'(\d+)\."', r'\1.0"', content_fixed)
    content_fixed = re.sub(r'(\d+)\.\s', r'\1.0 ', content_fixed)
    content_fixed = re.sub(r'(\d+)\.$', r'\1.0', content_fixed)
    
    processing_successful = False
    
    try:
        # Попробуем прочитать только часть файла, чтобы проверить структуру
        try:
            # Преобразуем исправленный JSON в словарь
            data = json.loads(content_fixed)
            print("JSON успешно прочитан полностью")
            processing_successful = True
        except json.JSONDecodeError as e:
            print(f"Проблема с полным файлом: {e}")
            print("Пробуем прочитать часть JSON, чтобы создать структуру DataFrame...")
            
            # Попробуем извлечь хотя бы базовую структуру и первые несколько элементов
            match = re.search(r'{\s*"price_list_date":\s*"([^"]+)",\s*"currency":\s*"([^"]+)"', content_fixed)
            if match:
                price_list_date = match.group(1)
                currency = match.group(2)
                
                # Создаем пустой DataFrame с нужной структурой
                df = pd.DataFrame(columns=['категория', 'подкатегория', 'артикул', 'наименование', 'цена', 'единица'])
                print("\nНе удалось загрузить JSON полностью, создан пустой DataFrame")
                print(f"Дата прайс-листа (из текста): {price_list_date}")
                print(f"Валюта (из текста): {currency}")
                
                # Пробуем прочитать данные при помощи pandas
                print("\nПробуем прочитать данные как CSV...")
                # Записываем временный файл
                temp_file = "temp_fixed.json" 
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content_fixed)
                
                # Попробуем прочитать данные напрямую как JSON lines
                try:
                    # Попробуем прочитать файл CSV через pandas с разными разделителями
                    try:
                        df_csv = pd.read_csv(file_path, nrows=5)
                        print("Удалось прочитать файл как CSV")
                        print(df_csv.head())
                    except:
                        print("Не удалось прочитать как обычный CSV")
                        
                    print("\nЗавершение работы с ошибкой.")
                    # Удаляем временный файл
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    processing_successful = False
                except Exception as e:
                    print(f"Ошибка при чтении файла как CSV: {str(e)}")
            else:
                print("Не удалось извлечь базовую информацию из JSON")
            
            # Если всё не получилось - выходим
            print("Обработка не может быть продолжена из-за ошибок с входными данными.")
            processing_successful = False
        
        # Если обработка успешна, продолжаем с данными JSON
        if processing_successful:
            # Выводим базовую информацию о данных
            print(f"Дата прайс-листа: {data.get('price_list_date')}")
            print(f"Валюта: {data.get('currency')}")
            
            # Преобразуем данные каталога в плоский список для создания DataFrame
            flat_data = []
            
            for category_name, subcategories in data.get('categories', {}).items():
                for subcategory_name, items in subcategories.items():
                    for item in items:
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
            
            # Сохраняем в CSV для возможного дальнейшего использования
            df.to_csv('processed_price_list.csv', index=False, encoding='utf-8')
            print("\nДанные сохранены в processed_price_list.csv")
        
    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")

print("Обработка завершена.") 