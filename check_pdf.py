import asyncio
from app.services.ocr_service import OCRService

ocr_service = OCRService()
import pymupdf # imports the pymupdf library

def prepare_pdf_to_images(pdf_path: str):
    doc = pymupdf.open(pdf_path) # open a document
    for page in doc: # iterate the document pages
        text = page.get_text() # get plain text encoded as UTF-8
        print(text + "================")


async def main():
    await ocr_service.process_document("Том 19 Шк-Ком-550-ОВ2.pdf", "Том 19 Шк-Ком-550-ОВ2.pdf")


if __name__ == "__main__":
    prepare_pdf_to_images("Том 19 Шк-Ком-550-ОВ2.pdf")

