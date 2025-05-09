# Архитектура сервисов LLM

## Общий обзор
Проект использует абстрактный слой для работы с различными LLM (Language Model) провайдерами, что обеспечивает гибкость и возможность легкой замены или добавления новых LLM-сервисов. Архитектура построена с использованием принципа абстракции и фабричного метода для создания экземпляров конкретных LLM-сервисов.

## Структура файлов

### `app/services/llm_work.py`
Абстрактный базовый класс, определяющий общий интерфейс для работы с любыми LLM-сервисами. Содержит абстрактные методы, которые должны быть реализованы в конкретных классах, и общую функциональность для всех LLM-сервисов:
- Инициализация с API ключом и моделью по умолчанию
- Абстрактные методы для отправки запросов к LLM
- Методы для форматирования ответов от LLM

### `app/services/openai_work.py`
Реализация интерфейса LLMWork для работы с OpenAI API. Поддерживает:
- Генерацию текста с историей сообщений (ChatCompletion)
- Простую генерацию текста (Completion)
- Генерацию эмбеддингов текста
- Распознавание и описание содержимого изображений

### `app/services/mistral_work.py`
Реализация интерфейса LLMWork для работы с Mistral AI API. Поддерживает:
- Генерацию текста с историей сообщений
- Простую генерацию текста
- Генерацию эмбеддингов текста
- Метод image_to_text (возвращает сообщение о неподдерживаемой функциональности)

### `app/services/llm_factory.py`
Фабрика для создания экземпляров LLM-сервисов:
- Регистрация доступных провайдеров LLM
- Получение экземпляра LLM-сервиса по имени провайдера
- Кэширование созданных экземпляров для экономии ресурсов
- Получение экземпляра LLM-сервиса по умолчанию на основе настроек приложения

## Диаграмма взаимодействия классов

```
┌─────────────┐          ┌─────────────┐
│ LLMFactory  │──────────▶ LLMWork     │
└─────────────┘          │ (Abstract)  │
      │                  └─────────────┘
      │                        ▲
      │                        │
      │                        │
      │                        │
      │                 ┌──────┴──────┐
      │                 │             │
      │                 │             │
┌─────▼─────┐     ┌─────▼─────┐     ┌─▼──────────┐
│ OpenAIWork│     │ MistralWork│     │ Другие LLM  │
└───────────┘     └───────────┘     └────────────┘
```

## Как использовать

### Получение экземпляра LLM-сервиса
```python
from app.services.llm_factory import LLMFactory

# Получение экземпляра OpenAI
openai_llm = LLMFactory.get_instance("openai")

# Получение экземпляра Mistral AI с указанием API ключа и модели
mistral_llm = LLMFactory.get_instance("mistral", api_key="your_key", model="mistral-medium")

# Получение экземпляра по умолчанию (на основе настроек приложения)
default_llm = LLMFactory.get_default_instance()
```

### Пример использования методов LLM-сервиса
```python
# Генерация текста с историей сообщений
messages = [
    {"role": "system", "content": "Вы - полезный ассистент."},
    {"role": "user", "content": "Привет, кто ты?"}
]
response = await llm.chat_completion(messages)
print(response["text"])

# Генерация текста без истории
response = await llm.completion("Объясни, что такое FastAPI")
print(response["text"])

# Получение эмбеддингов
texts = ["Первый текст", "Второй текст"]
embeddings = await llm.get_embeddings(texts)

# Распознавание изображения (только для OpenAI)
if isinstance(llm, OpenAIWork):
    description = await llm.image_to_text("path/to/image.jpg")
    print(description)
```

## Добавление нового LLM-провайдера
Для добавления нового LLM-провайдера необходимо:
1. Создать новый класс, наследующий `LLMWork`
2. Реализовать все абстрактные методы
3. Зарегистрировать новый класс в фабрике

```python
# Пример регистрации нового провайдера
from app.services.my_new_llm import MyNewLLM
LLMFactory.register_provider("my_provider", MyNewLLM)
``` 