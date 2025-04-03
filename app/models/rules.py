from typing import List, Optional, Dict
from pydantic import BaseModel


class RuleBlockResponse(BaseModel):
    """Модель ответа с блоком правил"""
    id: str
    title: str
    content: str


class RulesFileResponse(BaseModel):
    """Модель ответа со всеми блоками правил"""
    blocks: List[RuleBlockResponse]


class RuleBlockUpdateRequest(BaseModel):
    """Модель запроса на обновление блока правил"""
    title: Optional[str] = None
    content: Optional[str] = None


class RuleTypeResponse(BaseModel):
    """Модель для типа правил"""
    id: str
    name: str 