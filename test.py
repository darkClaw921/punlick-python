# -*- coding: utf-8 -*-
from mistralai import Mistral
from pprint import pprint

api_key = "m4xVHY7fWYwMH6OGTGlzoM41w4B6sNkn"
client = Mistral(api_key=api_key)
# file_path = "737 заявка-.pdf"
file_path = "test2.png"
# file_path = "наша 1 заявка-31-39.pdf"
print(file_path)
uploaded_pdf = client.files.upload(
    file={
        "file_name": file_path,
        "content": open(file_path, "rb"),
    },
    # purpose="ocr"
)
client.files.retrieve(file_id=uploaded_pdf.id)
signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
pprint(signed_url)
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": signed_url.url},
        ],
    }
]

# Get the chat response
chat_response = client.chat.complete(
    model="pixtral-12b-2409", messages=messages
)

# Print the content of the response
print(chat_response.choices[0].message.content)


1 / 0
# def get_all_image_in_pdf(pdf_path: str) -> list:
#     """Извлекает все изображения из PDF и сохраняет их в папку."""

#     import fitz  # PyMuPDF
#     import os
#     from PIL import Image
#     import io

#     # Создаем папку для изображений если её нет
#     images_dir = os.path.join(os.path.dirname(pdf_path), "images")
#     os.makedirs(images_dir, exist_ok=True)

#     # Открываем PDF
#     pdf_document = fitz.open(pdf_path)
#     saved_images = []

#     # Проходим по каждой странице
#     for page_num in range(pdf_document.page_count):
#         page = pdf_document[page_num]

#         # Получаем все изображения на странице
#         images = page.get_images()
#         svg_images = page.get_svg_image()

#         # Обрабатываем каждое изображение
#         for img_index, img in enumerate(images):
#             xref = img[0]
#             base_image = pdf_document.extract_image(xref)
#             image_bytes = base_image["image"]

#             # Конвертируем байты в изображение
#             image = Image.open(io.BytesIO(image_bytes))

#             # Формируем имя файла
#             image_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
#             image_path = os.path.join(images_dir, image_filename)

#             # Сохраняем изображение
#             image.save(image_path)
#             saved_images.append(image_path)

#         # Обрабатываем SVG изображения
#         if svg_images:
#             svg_filename = f"page_{page_num + 1}_svg.svg"
#             svg_path = os.path.join(images_dir, svg_filename)

#             # Сохраняем SVG
#             with open(svg_path, "wb") as f:
#                 a=str(svg_images)
#                 f.write(a.encode('utf-8'))  # Конвертируем строку в байты
#             saved_images.append(svg_path)
#     return saved_images

# images = get_all_image_in_pdf("наша 1 заявка-31-39.pdf")
# pprint(images)

# def extract_text_from_svg(svg_file_path: str) -> list[str]:
#     """
#     Извлекает весь текст из SVG файла.

#     Args:
#         svg_file_path (str): Путь к SVG файлу

#     Returns:
#         list[str]: Список найденных текстовых элементов
#     """
#     import xml.etree.ElementTree as ET

#     # Список для хранения найденного текста
#     text_elements = []

#     try:
#         # Парсим SVG файл
#         tree = ET.parse(svg_file_path)
#         root = tree.getroot()

#         # Находим все текстовые элементы в SVG
#         # Используем рекурсивный поиск по всем namespace
#         for elem in root.iter():
#             # Проверяем, является ли элемент текстовым
#             if elem.tag.endswith('}text') or elem.tag == 'text':
#                 if elem.text and elem.text.strip():
#                     text_elements.append(elem.text.strip())
#             # Проверяем tspan элементы, которые часто содержат текст в SVG
#             elif elem.tag.endswith('}tspan') or elem.tag == 'tspan':
#                 if elem.text and elem.text.strip():
#                     text_elements.append(elem.text.strip())

#     except ET.ParseError as e:
#         print(f"Ошибка при парсинге SVG файла {svg_file_path}: {e}")
#     except Exception as e:
#         print(f"Неожиданная ошибка при обработке файла {svg_file_path}: {e}")

#     return text_elements

# def convert_svg_to_png(svg_file_path: str) -> str:
#     """
#     Конвертирует SVG файл в PNG.

#     Args:
#         svg_file_path (str): Путь к SVG файлу

#     Returns:
#         str: Путь к созданному PNG файлу
#     """
#     import cairosvg

#     # Путь для сохранения PNG
#     png_file_path = svg_file_path.replace('.svg', '.png')

#     try:
#         # Конвертируем SVG в PNG
#         cairosvg.svg2png(url=svg_file_path, write_to=png_file_path)
#         print(f"Успешно конвертирован {svg_file_path} в {png_file_path}")
#         return png_file_path
#     except Exception as e:
#         print(f"Ошибка при конвертации SVG в PNG {svg_file_path}: {e}")
#         return None

# # Конвертируем все найденные SVG файлы в PNG
# png_files = []
# for image_path in images:
#     if image_path.endswith('.svg'):
#         # Извлекаем текст из SVG
#         texts = extract_text_from_svg(image_path)
#         print(f"\nТексты из файла {image_path}:")
#         for text in texts:
#             print(f"- {text}")

#         # Конвертируем SVG в PNG
#         png_path = convert_svg_to_png(image_path)
#         if png_path:
#             png_files.append(png_path)

# print("\nСозданные PNG файлы:")
# pprint(png_files)
