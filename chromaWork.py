import asyncio
import os
from pprint import pprint
import uuid
from app.core.config import settings
from mistralai import Mistral
import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from tqdm import tqdm
from typing import Dict, Any
import pandas as pd
from chromadb import Documents, EmbeddingFunction, Embeddings

mistral_client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))
def embedding_function(text:str):
    embeddings_response = mistral_client.embeddings.create(
                        model="mistral-embed",
                        inputs=[text]
                    )
    embedding = embeddings_response.data[0].embedding
    return embedding
class MyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        # embed the documents somehow
        return embedding_function(input)
class ChromaWork:
    def __init__(self,CHROMA_COLLECTION_NAME:str=os.environ.get("CHROMA_COLLECTION_NAME")):
        # Создаем директорию для векторной БД, если не существует
        self.CHROMA_COLLECTION_NAME = CHROMA_COLLECTION_NAME
        self.logger = logger
        os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
        # Пытаемся инициализировать Mistral API клиент
        self.mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        self.mistral_client = None
        if self.mistral_api_key:
            try:
                self.mistral_client = Mistral(api_key=self.mistral_api_key)
                self.mistral_model = "mistral-embed"  # Добавляем модель по умолчанию
                self.logger.info("Mistral API клиент успешно инициализирован")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать Mistral API клиент: {str(e)}")
        else:
            self.logger.warning("MISTRAL_API_KEY не найден в переменных окружения. Будет использована встроенная модель эмбеддингов.")

        # Словарь для хранения статусов загрузки
        self.upload_statuses = {}
        # Инициализация ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_DIR,
                settings=ChromaSettings(
                    allow_reset=True, anonymized_telemetry=False
                ),
            )

            # Получаем или создаем коллекцию
            try:
                self.collection = self.client.get_collection(
                    name=self.CHROMA_COLLECTION_NAME,
                    # embedding_function=MyEmbeddingFunction
                )
                self.logger.info(
                    f"Коллекция {self.CHROMA_COLLECTION_NAME} успешно подключена"
                )
            except:
                # Если используем Mistral для эмбеддингов, указываем это при создании коллекции
                if self.mistral_client:
                    self.collection = self.client.create_collection(
                        name=self.CHROMA_COLLECTION_NAME,
                        # metadata={
                        #     "description": "Коллекция товаров из прайс-листов",
                        #     # "embedding_model": "mistral-embed"
                        # },
                        # embedding_function=MyEmbeddingFunction
                    )
                else:
                    self.collection = self.client.create_collection(
                        name=self.CHROMA_COLLECTION_NAME,
                        # metadata={
                        #     "description": "Коллекция товаров из прайс-листов"
                        # },
                        # embedding_function=MyEmbeddingFunction
                    )
                self.logger.info(
                    f"Коллекция {self.CHROMA_COLLECTION_NAME} успешно создана"
                )

        except Exception as e:
            self.logger.error(f"Ошибка при инициализации ChromaDB: {str(e)}")
            raise Exception(f"Не удалось инициализировать ChromaDB: {str(e)}")
        
    @logger.catch
    async def add_items(self,text:str, separator:str="=========="):
        items = text.split(separator)
        print(len(items))   
        
        prepared_items = []
        embeddings = []
        for item in items:
            if not item.strip():  # Пропускаем пустые строки
                continue
            theme = item.split("===")[1]
            embeddings_response = await self.mistral_client.embeddings.create_async(
                        model="mistral-embed",
                        inputs=[theme.strip()]
                    )
            embedding = embeddings_response.data[0].embedding
            theme = theme.strip().replace("\n", "")
            prepared_items.append({
                "id": str(uuid.uuid4()),
                "document": theme,
                "metadata": {"promt": item}
            })
            embeddings.append(embedding)
            
        self.collection.add(
            ids=[pitem["id"] for pitem in prepared_items],
            documents=[pitem["document"] for pitem in prepared_items],
            metadatas=[pitem["metadata"] for pitem in prepared_items],
            embeddings=embeddings  # Передаем список эмбеддингов
        )
        
    def get_items(self,query:str,n_results:int=2, isReturnPromt:bool=False):
        embeddings = self.mistral_client.embeddings.create(
            model=self.mistral_model,
            inputs=[query]
        )
        # print(query)
        embeddings = embeddings.data[0].embedding
        # print(embeddings)
        if isReturnPromt:
            requests=self.collection.query(
                query_embeddings=[embeddings],
                n_results=n_results
            )
            # pprint(requests)
            return requests['metadatas'][0][0]["promt"]
        else:
            return self.collection.query(
                query_embeddings=[embeddings],
                n_results=n_results
            )
    def delete_collection(self):    
        self.logger.info(f"Удаление коллекции {self.CHROMA_COLLECTION_NAME}")        
        self.client.delete_collection(name=self.CHROMA_COLLECTION_NAME)
        a=self.client.list_collections()
        print(a)
    
if __name__ == "__main__":
    
    chromaWork = ChromaWork('test')
    chromaWork.delete_collection()
    chromaWork = ChromaWork('test') 
    asyncio.run(chromaWork.add_items(open("rules/новые правила пряямоугольных.txt", "r").read()))
    # chromaWork.add_items(open("rules/новые правила КРуглых.txt", "r").read())
    # chromaWork.delete_collection()
    # chromaWork.delete_collection()
    # pprint(chromaWork.get_items("врезка φ125/φ160", isReturnPromt=True))
    