# OCR Document Processor

Веб-приложение для обработки документов с помощью OCR Mistral и экспорта результатов в формате XLSX.

## Функциональность

- Загрузка файлов PDF и XLSX для распознавания
- Обработка документов через OCR Mistral
- Отображение результатов распознавания в табличном виде
- Экспорт результатов в формате XLSX (Название | Количество | Единица измерения)
- Загрузка прайс-листов в форматах JSON и CSV в векторную базу данных (ChromaDB)
- Семантический поиск похожих товаров по названию в прайс-листах

## Технологии

- Python 3.12
- FastAPI
- Bootstrap 5
- Jinja2 Templates
- openpyxl для работы с XLSX
- cairo для работы с SVG
- ChromaDB для векторного поиска товаров
- pandas для обработки CSV файлов

## Требования

- Python 3.12+
- uv (менеджер пакетов)

## Установка

1. Клонируйте репозиторий:
   ```
   git clone <repo-url>
   cd ocr-document-processor
   ```

2. Создайте и активируйте виртуальное окружение с помощью uv:
   ```
   uv venv
   source .venv/bin/activate  # для Linux/macOS
   # или
   .venv\Scripts\activate  # для Windows
   ```

3. Установите зависимости:
   ```
   uv pip install -e .
   ```

4. Настройте переменные окружения (скопируйте `.env.example` в `.env` и отредактируйте):
   ```
   cp .env.example .env
   ```
   
5. Укажите ваш ключ API Mistral в файле `.env`

Увеличьте лимит размера запроса на сервере:
sudo /etc/nginx/sites-available/orc-document.alteran-industries.ru.conf
Если используете Nginx, добавьте в конфигурацию client_max_body_size 20M;
Если используете Apache, добавьте в .htaccess LimitRequestBody 20971520
Если используете Express.js, настройте лимит: app.use(express.json({ limit: '20mb' }))

## Запуск приложения

```
python -m app.main
```

или

```
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу http://localhost:8000

## API Endpoints

- `POST /api/documents/upload` - Загрузка документа для обработки
- `GET /api/documents/{document_id}` - Получение результатов обработки
- `POST /api/documents/{document_id}/export` - Экспорт результатов в XLSX
- `GET /api/exports/{filename}` - Скачивание экспортированного файла
- `POST /api/price-list/upload` - Загрузка прайс-листа в векторную базу данных
- `POST /api/price-list/search` - Поиск похожих товаров в прайс-листах

## Формат прайс-листа

Поддерживаются два формата прайс-листов:

### JSON 

```json
{
  "price_list_date": "2023-01-01",
  "currency": "RUB",
  "categories": {
    "Категория1": {
      "Подкатегория1": [
        {
          "article": "ABC-123",
          "name": "Название товара",
          "price": 123.45,
          "unit": "шт"
        }
      ]
    }
  }
}
```

### CSV

CSV файл должен содержать следующие колонки:
- category - категория товара
- subcategory - подкатегория товара
- article - артикул товара
- name - название товара
- price - цена товара
- unit - единица измерения
- price_list_date (необязательно) - дата прайс-листа
- currency (необязательно) - валюта

## Структура проекта

```
app/
├── api/             # API маршруты
├── core/            # Конфигурации и настройки
├── models/          # Модели данных
├── services/        # Бизнес-логика
├── static/          # Статические файлы (CSS, JS)
│   ├── css/
│   └── js/
├── templates/       # HTML шаблоны
└── main.py          # Точка входа приложения
vectordb/           # Директория для хранения данных ChromaDB
uploads/            # Директория для загруженных файлов
exports/            # Директория для экспортированных файлов
```

# Система обработки и валидации прайс-листов

Данный проект представляет собой систему обработки, распознавания и валидации прайс-листов для элементов вентиляции и других строительных материалов.

## Основные возможности

- Распознавание товаров из разных форматов прайс-листов
- Поиск соответствий в векторной базе эталонных наименований
- Автоматическая валидация и корректировка наименований согласно правилам
- Интеграция результатов в единый процесс обработки данных

## Новые компоненты

### Валидатор прямоугольных элементов вентиляции

Добавлен модуль для проверки и корректировки наименований прямоугольных элементов вентиляции согласно стандартам:

- `rectangular_item_validator.py` - Основные валидаторы для различных типов элементов ПР
- `price_validator_service.py` - Сервис для интеграции валидаторов в основной процесс
- `integration_example.py` - Пример использования обоих методов (поиск соответствий + валидация)

#### Поддерживаемые типы элементов:

- Заглушки ПР
- Воздуховоды ПР
- Отводы угловые ПР
- Отводы радиусные ПР
- Тройники ПР
- Тройники ПР с КР врезкой
- Переходы ПР
- Переходы с ПР на КР
- Врезки ПР в площадку
- Врезки с отбортовкой ПР
- Зонты крышные ПР
- Адаптеры ПР
- Дроссель-клапаны ПР
- Обратные клапаны ПР
- Шумоглушители пластинчатые ПР

## Использование

### Пример использования валидатора отдельно:

```python
from rectangular_item_validator import RectangularItemValidator

validator = RectangularItemValidator()
is_valid, correct_name, error = validator.validate_item("Заглушка 400*300")

if is_valid:
    print(f"Правильное наименование: {correct_name}")
else:
    print(f"Ошибка: {error}")
```

### Пример интеграции обоих методов:

```python
from price_list_service import PriceListService
from price_validator_service import PriceValidatorService

# Инициализируем оба сервиса
price_service = PriceListService()
validator_service = PriceValidatorService()

# Обрабатываем данные с использованием обоих методов
enriched_items = await price_service.find_matching_items(items, 0.7)
final_items = await validator_service.integrate_with_matching_service(
    items, enriched_items, 0.7
)
```

## Установка и запуск

1. Клонировать репозиторий
2. Установить зависимости: `pip install -e .`
3. Запустить пример интеграции: `python integration_example.py` 