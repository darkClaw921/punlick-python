import os
import uuid
import json
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment

from app.core.config import settings
from app.models.document import DocumentResponse


class ExportService:
    """Сервис для экспорта результатов в XLSX"""

    def __init__(self):
        self.export_dir = settings.EXPORT_DIR
        os.makedirs(self.export_dir, exist_ok=True)

    async def export_to_xlsx(self, document_response: DocumentResponse) -> str:
        """Экспортирует результаты в XLSX файл и возвращает путь к файлу"""

        # Создаем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}_{uuid.uuid4().hex[:8]}.xlsx"
        filepath = os.path.join(self.export_dir, filename)

        # Создаем новую книгу Excel
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Результаты OCR"

        # Добавляем заголовок
        sheet["A1"] = "Название"
        sheet["B1"] = "Количество"
        sheet["C1"] = "Ед. изм."

        # Форматирование заголовков
        header_font = Font(bold=True)
        for cell in sheet["1:1"]:
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # Заполняем данными
        row_num = 2
        for item in document_response.items:
            try:
                # Пытаемся распарсить JSON из текстового поля
                product_data = json.loads(item.text)

                # Записываем данные в соответствующие ячейки
                sheet[f"A{row_num}"] = product_data.get("Наименование", "")
                sheet[f"B{row_num}"] = product_data.get("Количество", "")
                sheet[f"C{row_num}"] = product_data.get("Ед.изм.", "")
            except (json.JSONDecodeError, AttributeError):
                # Если не удалось распарсить как JSON, записываем весь текст в первую колонку
                sheet[f"A{row_num}"] = item.text
                sheet[f"B{row_num}"] = ""
                sheet[f"C{row_num}"] = ""

            row_num += 1

        # Форматирование ячеек
        for row in sheet.iter_rows(min_row=2, max_row=row_num - 1):
            for cell in row:
                cell.alignment = Alignment(horizontal="left")

        # Автоподбор ширины столбцов
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = max_length + 2
            sheet.column_dimensions[column_letter].width = adjusted_width

        # Сохраняем файл
        workbook.save(filepath)

        return filename


# Создаем экземпляр сервиса
export_service = ExportService()
