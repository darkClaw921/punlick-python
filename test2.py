# -*- coding: utf-8 -*-
import asyncio
import json
from mistralai import Mistral
from pprint import pprint
api_key = "m4xVHY7fWYwMH6OGTGlzoM41w4B6sNkn"
client = Mistral(api_key=api_key)

file_path = "test.png"


async def prepare_text_anserw_to_dict(text: str) -> list[dict[str, str]]:
    text=text.replace("```json", "").replace("```", "")
    text=text.strip()
    return json.loads(text)

async def process_image(self, file_path: str, original_filename: str) -> DocumentResponse:
    uploaded_pdf = client.files.upload(
        file={
        
            "file_name": "test.png",
            "content": open(file_path, "rb"),
        },
        purpose="ocr"
    )  
    client.files.retrieve(file_id=uploaded_pdf.id)
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    # signed_url = "https://api.mistral.ai/v1/files/f1234567890/signed_url"
    pprint(signed_url)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "найди все товары и верни их в виде списка в формате json Наименование|Количество|Ед.изм."
                },
                {
                    "type": "image_url",
                    "image_url": signed_url.url
                }
            ]
        }
    ]

    # Get the chat response
    chat_response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=messages
    )

    # Print the content of the response
    text=chat_response.choices[0].message.content

    pprint(prepare_text_anserw_to_dict(text))
    return prepare_text_anserw_to_dict(text)
    
async def process_document(self, file_path: str, original_filename: str) -> DocumentResponse:
        """Обработка документа с использованием Mistral OCR API"""
        try:
            # Загрузка файла в Mistral
            uploaded_file = self._client.files.upload(
                file={
                    "file_name": original_filename,
                    "content": open(file_path, "rb"),
                },
                purpose="ocr"
            )

            # Получение подписанного URL для доступа к файлу
            signed_url = self._client.files.get_signed_url(file_id=uploaded_file.id)

            # Обработка документа через OCR
            ocr_response = self._client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": signed_url.url,
                },
                include_image_base64=True
            )
            
            # Создание ответа
            document_response = DocumentResponse(
                id=uploaded_file.id,
                original_filename=original_filename,
                items=[DocumentItem(text=page.markdown) for page in ocr_response.pages]
            )

            # Сохранение результата
            self._results[uploaded_file.id] = document_response
            
            return document_response

        except Exception as e:
            logger.error(f"Ошибка при обработке документа {original_filename}: {str(e)}")
            raise