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


class NewRuleBlockRequest(BaseModel):
    """Модель запроса на создание нового блока правил"""
    file_type: str
    title: str
    content: str


class NewRuleFileRequest(BaseModel):
    """Модель запроса на создание нового файла правил"""
    file_type: str
    file_name: str
    display_name: str 