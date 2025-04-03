import os
from typing import List, Dict, Tuple, Optional
import uuid
import hashlib
from pydantic import BaseModel
from fastapi import HTTPException

class RuleBlock(BaseModel):
    """Модель для блока правил"""
    id: str
    title: str
    content: str

class RulesFile(BaseModel):
    """Модель для файла правил"""
    blocks: List[RuleBlock]

class RulesService:
    """Сервис для работы с файлом правил"""
    
    def __init__(self):
        self.rules_files = {
            "round": os.path.join(os.getcwd(), "новые правила КРуглых.txt"),
            "rectangular": os.path.join(os.getcwd(), "новые правила пряямоугольных.txt")
        }
        self.block_separator = "=========="
        self.title_separator = "==="
        
    def parse_rules_file(self, file_type: str = "round") -> RulesFile:
        """Парсинг файла правил"""
        try:
            # Проверяем существование типа файла
            if file_type not in self.rules_files:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неизвестный тип файла правил: {file_type}. Доступные типы: {', '.join(self.rules_files.keys())}"
                )
                
            rules_file_path = self.rules_files[file_type]
            
            with open(rules_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Разделяем файл на блоки по разделителю ==========
            blocks_raw = content.split(self.block_separator)
            
            rules_blocks = []
            
            for i, block_raw in enumerate(blocks_raw):
                if not block_raw.strip():
                    continue
                    
                # Находим заголовок блока между === и ===
                parts = block_raw.split(self.title_separator)
                
                if len(parts) >= 3:
                    # Заголовок находится между первым и вторым ===
                    title = parts[1].strip()
                    
                    # Содержимое - это все, что после второго ===
                    content = self.title_separator.join(parts[2:]).strip()
                    
                    # Генерируем стабильный ID на основе заголовка и содержимого
                    content_hash = hashlib.md5((title + content).encode('utf-8')).hexdigest()
                    stable_id = f"rule-{file_type}-{content_hash}"
                    
                    rules_blocks.append(RuleBlock(
                        id=stable_id,
                        title=title,
                        content=content
                    ))
                
            return RulesFile(blocks=rules_blocks)
                
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при чтении файла правил: {str(e)}"
            )
    
    def save_rules_file(self, file_type: str, rules_file: RulesFile) -> bool:
        """Сохранение изменений в файл правил"""
        try:
            # Проверяем существование типа файла
            if file_type not in self.rules_files:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неизвестный тип файла правил: {file_type}. Доступные типы: {', '.join(self.rules_files.keys())}"
                )
                
            rules_file_path = self.rules_files[file_type]
            
            content_parts = []
            
            for block in rules_file.blocks:
                # Формируем блок правил
                block_content = f"{self.title_separator}\n{block.title}\n{self.title_separator}\n{block.content}"
                content_parts.append(block_content)
            
            # Объединяем все блоки с разделителем
            full_content = f"\n{self.block_separator}\n".join(content_parts)
            
            with open(rules_file_path, 'w', encoding='utf-8') as file:
                file.write(full_content)
                
            return True
                
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при сохранении файла правил: {str(e)}"
            )
    
    def get_rule_block(self, block_id: str) -> Optional[RuleBlock]:
        """Получение блока правил по ID"""
        # ID имеет формат rule-{file_type}-{hash}
        parts = block_id.split('-', 2)
        if len(parts) < 3 or parts[0] != "rule":
            return None
            
        file_type = parts[1]
        
        # Получаем все правила из файла соответствующего типа
        rules_file = self.parse_rules_file(file_type)
        
        for block in rules_file.blocks:
            if block.id == block_id:
                return block
                
        return None
    
    def update_rule_block(self, block_id: str, title: str = None, content: str = None) -> bool:
        """Обновление блока правил"""
        # ID имеет формат rule-{file_type}-{hash}
        parts = block_id.split('-', 2)
        if len(parts) < 3 or parts[0] != "rule":
            return False
            
        file_type = parts[1]
        
        rules_file = self.parse_rules_file(file_type)
        
        updated = False
        for i, block in enumerate(rules_file.blocks):
            if block.id == block_id:
                if title is not None:
                    rules_file.blocks[i].title = title
                if content is not None:
                    rules_file.blocks[i].content = content
                updated = True
                break
        
        if updated:
            return self.save_rules_file(file_type, rules_file)
        
        return False
        
    def get_available_rule_types(self) -> Dict[str, str]:
        """Получение доступных типов файлов правил"""
        return {
            "round": "Правила для круглых элементов",
            "rectangular": "Правила для прямоугольных элементов"
        }

# Создаем экземпляр сервиса
rules_service = RulesService() 