"""Сервис для работы с OpenAI API"""
import os
import base64
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.services.llms.llm_work import LLMWork
from app.core.config import settings

# MODEL="gpt-4.1-nano-2025-04-14"
MODEL="gpt-4o-mini"
class OpenAIWork(LLMWork):
    """
    Реализация работы с OpenAI API
    Поддерживает модели OpenAI для чата, завершения текста, эмбеддингов и работы с изображениями
    """

    def __init__(self, api_key: Optional[str] = None, model: str = MODEL):
    # def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-nano"):
        """
        Инициализация клиента OpenAI

        Args:
            api_key: API ключ для доступа к OpenAI API (если None, будет использован из переменных окружения)
            model: Модель по умолчанию
        """
        super().__init__(api_key, model)
        # Используем API ключ из аргументов или из конфигурации приложения
        self.api_key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        self.model = model
        if not self.api_key:
            self.logger.warning("API ключ OpenAI не найден. Некоторые функции могут быть недоступны.")
        
        # Инициализация клиента OpenAI
        try:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.logger.info("Клиент OpenAI успешно инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации клиента OpenAI: {str(e)}")
            self.client = None

    async def chat_completion(self, messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            temperature: float = 0.9, 
                            max_tokens: int = 16000) -> Dict[str, Any]:
        """
        Отправляет запрос на генерацию текста с историей сообщений через OpenAI ChatCompletion API

        Args:
            messages: Список сообщений для контекста
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Форматированный ответ от OpenAI
        """
        if not self.client:
            self.logger.error("Клиент OpenAI не инициализирован")
            return {"text": "", "error": "Клиент OpenAI не инициализирован"}
        
        if model is None:
            model=MODEL
        self.logger.info(f"Вызов chat_completion с моделью: {model}")
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                # max_tokens=max_tokens
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
        Отправляет запрос на генерацию текста без истории через OpenAI ChatCompletion API
        Обернуто в формат чата для совместимости с новым API

        Args:
            prompt: Текст запроса
            model: Модель для использования
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Dict: Форматированный ответ от OpenAI
        """
        # Для новых версий API OpenAI используем chat_completion
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(
            messages=messages,
            model=MODEL,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return self.format_response(response)
    
    async def get_embeddings(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """
        Генерирует эмбеддинги для списка текстов через OpenAI Embeddings API

        Args:
            texts: Список текстов для генерации эмбеддингов
            model: Модель для использования (по умолчанию text-embedding-ada-002)

        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        if not self.client:
            self.logger.error("Клиент OpenAI не инициализирован")
            return []
        
        embedding_model = model or "text-embedding-ada-002"
        
        try:
            # Обрабатываем тексты пакетами для оптимизации запросов
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                response = await self.client.embeddings.create(
                    model=embedding_model,
                    input=batch_texts
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении эмбеддингов через OpenAI API: {str(e)}")
            return []
    
    async def image_to_text(self, image_path: str, prompt: Optional[str] = None) -> str:
        """
        Распознает и описывает содержимое изображения через OpenAI Vision API

        Args:
            image_path: Путь к изображению
            prompt: Дополнительные инструкции для распознавания (если None, используется "Опиши подробно, что изображено на фото")

        Returns:
            str: Текстовое описание изображения
        """
        if not self.client:
            self.logger.error("Клиент OpenAI не инициализирован")
            return "Ошибка: Клиент OpenAI не инициализирован"
        
        if not os.path.exists(image_path):
            self.logger.error(f"Изображение не найдено: {image_path}")
            return f"Ошибка: Изображение не найдено: {image_path}"
        
        try:
            # Загружаем изображение и кодируем в base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            

            # Подготавливаем сообщение с изображением
            content_parts =[
                {
                    "role": "user",
                    "content": [
                        { "type": "input_text", "text": prompt or "Опиши подробно, что изображено на фото" },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    ],
                }
            ]

            
            # Отправляем запрос
            # response = await self.client.chat.completions.create(
            response = await self.client.responses.create(
                # model=self.model,
                model='gpt-4.1-nano',
                input=content_parts,
                # max_tokens=1000
            )
            # from pprint import pprint
            # pprint(response)
            # Извлекаем описание
            formatted_response = self.format_response(response, True)
            return formatted_response
            
        except Exception as e:
            self.logger.error(f"Ошибка при распознавании изображения: {str(e)}")
            return f"Ошибка при распознавании изображения: {str(e)}"
    
    def _extract_text(self, response: Any, isImage: bool = False) -> str:
        """
        Извлекает текст из ответа OpenAI
        
        Args:
            response: Ответ от OpenAI API
            
        Returns:
            str: Извлеченный текст
        """
        try:
            if isImage:
                return response.output_text
            else:
                return response.choices[0].message.content
        except:
            return ""
    
    def _extract_tokens(self, response: Any) -> int:
        """
        Извлекает количество использованных токенов
        
        Args:
            response: Ответ от OpenAI API
            
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
            response: Ответ от OpenAI API
            
        Returns:
            str: Причина завершения
        """
        try:
            return response.choices[0].finish_reason
        except:
            return "unknown" 