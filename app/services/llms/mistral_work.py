"""Сервис для работы с Mistral AI API"""
import os
from typing import List, Dict, Any, Optional
from mistralai import Mistral
# from mistralai.models.chat_completion import ChatMessage
from app.services.llms.llm_work import LLMWork
from app.core.config import settings


class MistralWork(LLMWork):
    """
    Реализация работы с Mistral AI API
    Поддерживает модели Mistral для чата и эмбеддингов
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest"):
        """
        Инициализация клиента Mistral AI

        Args:
            api_key: API ключ для доступа к Mistral AI API (если None, будет использован из переменных окружения)
            model: Модель по умолчанию
        """
        super().__init__(api_key, model)
        # Используем API ключ из аргументов или из конфигурации приложения
        self.api_key = api_key or settings.MISTRAL_API_KEY or os.environ.get("MISTRAL_API_KEY")
        
        if not self.api_key:
            self.logger.warning("API ключ Mistral AI не найден. Некоторые функции могут быть недоступны.")
        
        # Инициализация клиента Mistral AI
        try:
            self.client = Mistral(api_key=self.api_key)
            self.logger.info("Клиент Mistral AI успешно инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации клиента Mistral AI: {str(e)}")
            self.client = None

    async def chat_completion(self, messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            temperature: float = 0.7, 
                            max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Отправляет запрос на генерацию текста с историей сообщений через Mistral AI ChatCompletion API

        Args:
            messages: Список сообщений для контекста
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Форматированный ответ от Mistral AI
        """
        if not self.client:
            self.logger.error("Клиент Mistral AI не инициализирован")
            return {"text": "", "error": "Клиент Mistral AI не инициализирован"}
        
        try:
            # Преобразуем формат сообщений для Mistral API
            # chat_messages = [
            #     {"role": "system", "content": "Вы - полезный ассистент."},
            #     {"role": "user", "content": "Привет, кто ты?"}
            # ]
            
            response = await self.client.chat.complete_async(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return self.format_response(response)
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении chat_completion: {str(e)}")
            return {"text": "", "error": str(e)}
    
    async def completion(self, prompt: str, 
                       model: Optional[str] = None,
                       temperature: float = 0.7, 
                       max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Отправляет запрос на генерацию текста без истории через Mistral AI ChatCompletion API
        Обернуто в формат чата

        Args:
            prompt: Текст запроса
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Форматированный ответ от Mistral AI
        """
        # Преобразуем одиночный запрос в формат чата
        messages = [{"role": "user", "content": prompt}]
        response =  await self.client.chat.complete_async(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return self.format_response(response)
    
    async def get_embeddings(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """
        Генерирует эмбеддинги для списка текстов через Mistral AI Embeddings API

        Args:
            texts: Список текстов для генерации эмбеддингов
            model: Модель для использования (по умолчанию "mistral-embed")

        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        if not self.client:
            self.logger.error("Клиент Mistral AI не инициализирован")
            return []
        
        embedding_model = model or "mistral-embed"
        
        try:
            # Обрабатываем тексты пакетами для оптимизации запросов
            batch_size = 20
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                response = await self.client.embeddings.create_async(
                    model=embedding_model,
                    input=batch_texts
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении эмбеддингов через Mistral AI API: {str(e)}")
            return []
    
    async def image_to_text(self, image_path: str, prompt: Optional[str] = None) -> str:
        """
        Распознавание изображений не поддерживается Mistral AI на данный момент.
        
        Args:
            image_path: Путь к изображению
            prompt: Дополнительные инструкции для распознавания

        Returns:
            str: Сообщение об ошибке
        """
        uploaded_pdf = await self.client.files.upload_async(
            file={
                "file_name": image_path,
                "content": open(image_path, "rb"),
            },
            purpose="ocr",
        )
        await self.client.files.retrieve_async(file_id=uploaded_pdf.id)
        signed_url = await self.client.files.get_signed_url_async(
            file_id=uploaded_pdf.id
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        # "text": 'найди все позиции и верни их в виде списка в формате json "Наименование": наиминование, "Количество": количество, "Ед.изм.": ед.изм. даже если это 1 элемент то верни 1 элемент' ,
                        "text": prompt
                    },
                    {"type": "image_url", "image_url": signed_url.url},
                ],
            }
        ]

        # Get the chat response
        chat_response = await self.client.chat.complete_async(
            model="pixtral-12b-2409", messages=messages
        )

        # Print the content of the response
        response = self.format_response(chat_response)

        return response
    
    def _extract_text(self, response: Any) -> str:
        """
        Извлекает текст из ответа Mistral AI
        
        Args:
            response: Ответ от Mistral AI API
            
        Returns:
            str: Извлеченный текст
        """
        try:
            return response.choices[0].message.content
        except:
            return ""
    
    def _extract_tokens(self, response: Any) -> int:
        """
        Извлекает количество использованных токенов
        
        Args:
            response: Ответ от Mistral AI API
            
        Returns:
            int: Количество использованных токенов
        """
        try:
            return response.usage.total_tokens
        except:
            return 0
    
    def _extract_finish_reason(self, response: Any) -> str:
        """
        Извлекает причину завершения генерации
        
        Args:
            response: Ответ от Mistral AI API
            
        Returns:
            str: Причина завершения
        """
        try:
            return response.choices[0].finish_reason
        except:
            return "unknown" 