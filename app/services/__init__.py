"""
Пакет сервисов приложения
Содержит сервисы для работы с различными компонентами приложения
"""

# Модуль для работы с LLM сервисами
from app.services.llms.llm_work import LLMWork
from app.services.llms.openai_work import OpenAIWork
from app.services.llms.mistral_work import MistralWork
from app.services.llms.llm_factory import LLMFactory

# Предоставляем удобный доступ к фабрике
get_llm = LLMFactory.get_instance
get_default_llm = LLMFactory.get_default_instance

# Сервисы для обработки бизнес-логики
from app.services.rules_service import rules_service
