from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Типы поддерживаемых документов"""

    PDF = "pdf"
    XLSX = "xlsx"
    IMAGE = "image"
    TEXT = "text"  # Новый тип для текстовых сообщений
    PRICE_LIST = "price_list"  # Новый тип для прайс-листов


class DocumentItem(BaseModel):
    """Модель для элемента документа (страницы)"""

    text: str


class DocumentUpload(BaseModel):
    """Модель для загрузки документа"""

    filename: str
    file_type: DocumentType
    file_size: int


class DocumentResponse(BaseModel):
    """Модель ответа с результатами обработки документа"""

    id: str
    original_filename: str
    items: List[DocumentItem]
    status: str = "completed"
    error: Optional[str] = None


class ExportRequest(BaseModel):
    """Запрос на экспорт результатов в XLSX"""

    document_id: str


class ExportResponse(BaseModel):
    """Модель ответа с информацией об экспорте"""

    export_filename: str
    download_url: str


class PriceListItem(BaseModel):
    """Модель для товара из прайс-листа"""

    article: str
    name: str
    price: float
    unit: Optional[str] = None


class PriceListCategory(BaseModel):
    """Модель для категории товаров в прайс-листе"""

    items: List[PriceListItem]


class PriceListUpload(BaseModel):
    """Модель для загрузки прайс-листа"""

    price_list_date: str
    currency: str
    categories: Dict[str, Dict[str, List[PriceListItem]]]


class PriceListResponse(BaseModel):
    """Модель ответа с информацией о загруженном прайс-листе"""

    id: str
    filename: str
    date: str
    currency: str
    total_items: int
    categories_count: int
    status: str = "completed"
    error: Optional[str] = None


class PriceListSearchQuery(BaseModel):
    """Модель для поиска товаров в прайс-листе"""

    query: str
    limit: int = 10
    supplier_id: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    category: Optional[str] = None
