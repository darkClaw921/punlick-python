"""Фабрика для создания экземпляров LLM сервисов"""
from typing import Dict, Any, Optional, Union
import os
from loguru import logger
from app.services.llms.llm_work import LLMWork
from app.services.llms.openai_work import OpenAIWork
from app.services.llms.mistral_work import MistralWork
from app.core.config import settings


class LLMFactory:
    """
    Фабрика для создания и управления экземплярами LLM сервисов
    Позволяет получить нужный тип LLM по имени
    """
    
    # Словарь для хранения зарегистрированных провайдеров LLM
    _providers = {
        "openai": OpenAIWork,
        "mistral": MistralWork,
    }
    
    # Кэш экземпляров для повторного использования
    _instances = {}
    
    @classmethod
    def get_instance(cls, provider: str, api_key: Optional[str] = None, model: Optional[str] = None) -> LLMWork:
        """
        Получает экземпляр LLM сервиса по имени провайдера

        Args:
            provider: Имя провайдера LLM ("openai", "mistral", и т.д.)
            api_key: API ключ (опционально)
            model: Модель по умолчанию (опционально)

        Returns:
            LLMWork: Экземпляр LLM сервиса
        """
        provider = provider.lower()
        
        # Проверяем, существует ли провайдер
        if provider not in cls._providers:
            logger.error(f"Провайдер LLM '{provider}' не найден. Доступные провайдеры: {list(cls._providers.keys())}")
            raise ValueError(f"Неизвестный провайдер LLM: {provider}")
        
        # Генерируем ключ для кэша
        cache_key = f"{provider}_{api_key or 'default'}_{model or 'default'}"
        
        # Проверяем, есть ли уже экземпляр в кэше
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Создаем новый экземпляр
        provider_class = cls._providers[provider]
        instance = provider_class(api_key=api_key, model=model)
        
        # Сохраняем в кэше
        cls._instances[cache_key] = instance
        
        return instance
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """
        Регистрирует новый класс провайдера LLM

        Args:
            name: Имя провайдера
            provider_class: Класс провайдера, наследник LLMWork
        """
        if not issubclass(provider_class, LLMWork):
            raise TypeError(f"Класс провайдера должен быть наследником LLMWork")
        
        cls._providers[name.lower()] = provider_class
        logger.info(f"Провайдер LLM '{name}' успешно зарегистрирован")
    
    @classmethod
    def get_default_instance(cls) -> LLMWork:
        """
        Получает экземпляр LLM сервиса по умолчанию на основе настроек приложения

        Returns:
            LLMWork: Экземпляр LLM сервиса по умолчанию
        """
        # Определяем провайдер по умолчанию из настроек
        default_provider = getattr(settings, "DEFAULT_LLM_PROVIDER", "openai").lower()
        
        # Если провайдер не существует, используем OpenAI
        if default_provider not in cls._providers:
            logger.warning(f"Провайдер LLM '{default_provider}' не найден, используется OpenAI")
            default_provider = "openai"
        
        # Получаем API ключ для провайдера из настроек
        api_key = None
        if default_provider == "openai":
            api_key = getattr(settings, "OPENAI_API_KEY", None)
        elif default_provider == "mistral":
            api_key = getattr(settings, "MISTRAL_API_KEY", None)
        
        # Получаем модель по умолчанию из настроек
        default_model = getattr(settings, f"DEFAULT_{default_provider.upper()}_MODEL", None)
        
        # Возвращаем экземпляр
        return cls.get_instance(default_provider, api_key, default_model) 