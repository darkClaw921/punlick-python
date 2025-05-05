"""Абстрактный класс для работы с различными LLM сервисами"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import os
from loguru import logger


class LLMWork(ABC):
    """
    Абстрактный класс для работы с LLM моделями
    От него наследуются конкретные реализации для разных провайдеров (OpenAI, Mistral и т.д.)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация базового класса LLM

        Args:
            api_key: API ключ для доступа к LLM сервису
            model: Модель по умолчанию
        """
        self.api_key = api_key
        self.model = model
        self.client = None
        self.logger = logger.bind(context="llm_service")
        
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            temperature: float = 0.9, 
                            max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Отправляет запрос на генерацию текста с историей сообщений

        Args:
            messages: Список сообщений для контекста
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Ответ от LLM модели
        """
        pass
    
    @abstractmethod
    async def completion(self, prompt: str, 
                       model: Optional[str] = None,
                       temperature: float = 0.9, 
                       max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Отправляет запрос на генерацию текста без истории

        Args:
            prompt: Текст запроса
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Ответ от LLM модели
        """
        pass
    
    @abstractmethod
    async def get_embeddings(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """
        Генерирует эмбеддинги для списка текстов

        Args:
            texts: Список текстов для генерации эмбеддингов
            model: Модель для использования

        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        pass
    
    @abstractmethod
    async def image_to_text(self, image_path: str, prompt: Optional[str] = None) -> str:
        """
        Распознает и описывает содержимое изображения

        Args:
            image_path: Путь к изображению
            prompt: Дополнительные инструкции для распознавания

        Returns:
            str: Текстовое описание изображения
        """
        pass
    
    def format_response(self, response: Any, isImage: bool = False) -> Dict[str, Any]:
        """
        Форматирует ответ от LLM модели в унифицированный формат

        Args:
            response: Ответ от LLM модели

        Returns:
            Dict: Форматированный ответ
        """
        try:
            # Базовая реализация, которую можно переопределить
            return {
                "text": self._extract_text(response, isImage),
                "tokens": self._extract_tokens(response),
                "finish_reason": self._extract_finish_reason(response),
                "raw_response": response
            }
        except Exception as e:
            self.logger.error(f"Ошибка при форматировании ответа: {str(e)}")
            return {"text": "", "error": str(e), "raw_response": response}
    
    def _extract_text(self, response: Any, isImage: bool = False) -> str:
        """
        Извлекает текст из ответа модели
        
        Args:
            response: Ответ от LLM модели
            
        Returns:
            str: Извлеченный текст
        """
        # Переопределяется в конкретных реализациях
        return ""
    
    def _extract_tokens(self, response: Any) -> int:
        """
        Извлекает количество использованных токенов
        
        Args:
            response: Ответ от LLM модели
            
        Returns:
            int: Количество использованных токенов
        """
        # Переопределяется в конкретных реализациях
        return 0
    
    def _extract_finish_reason(self, response: Any) -> str:
        """
        Извлекает причину завершения генерации
        
        Args:
            response: Ответ от LLM модели
            
        Returns:
            str: Причина завершения
        """
        # Переопределяется в конкретных реализациях
        return "unknown"
