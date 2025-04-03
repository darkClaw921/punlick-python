import os
import glob
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
    """Сервис для работы с файлами правил"""
    
    def __init__(self):
        # Директория для файлов правил
        self.rules_dir = os.path.join(os.getcwd(), "rules")
        
        # Создаем директорию, если ее нет
        if not os.path.exists(self.rules_dir):
            os.makedirs(self.rules_dir, exist_ok=True)
        
        # Инициализируем словарь файлов правил
        self.rules_files = {}
        
        # Загружаем все текстовые файлы из директории rules
        self.load_rule_files()
        
        self.block_separator = "=========="
        self.title_separator = "==="
    
    def load_rule_files(self) -> None:
        """Загружает все текстовые файлы из директории rules"""
        # Сбрасываем словарь
        self.rules_files = {}
        
        # Ищем все текстовые файлы
        for file_path in glob.glob(os.path.join(self.rules_dir, "*.txt")):
            file_name = os.path.basename(file_path)
            # Извлекаем тип правил из имени файла
            rule_type = self.get_rule_type_from_filename(file_name)
            # Добавляем в словарь
            self.rules_files[rule_type] = file_path
    
    def get_rule_type_from_filename(self, filename: str) -> str:
        """Получает тип правил из имени файла"""
        # Удаляем расширение и разделяем по пробелам
        base_name = os.path.splitext(filename)[0]
        
        # Если в имени есть 'правила', используем последнее слово как тип
        if 'правила' in base_name.lower():
            parts = base_name.lower().split()
            try:
                # Находим позицию слова "правила"
                idx = parts.index('правила')
                # Если после слова "правила" есть еще слова, берем следующее
                if idx < len(parts) - 1:
                    return parts[idx + 1]
            except ValueError:
                # Если слово "правила" не найдено точно, ищем частичное совпадение
                for i, part in enumerate(parts):
                    if 'правила' in part and i < len(parts) - 1:
                        return parts[i + 1]
        
        # Если не смогли определить, используем имя файла без расширения
        # и удаляем слова "новые" и "правила" если они есть
        clean_name = base_name.lower()
        for prefix in ['новые', 'правила', 'новые правила']:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):].strip()
        
        # Если в имени есть тип элементов, возвращаем его
        for element_type in ['круглых', 'прямоугольных', 'квадратных', 'овальных']:
            if element_type in clean_name:
                return element_type
        
        # Если все методы не сработали, возвращаем имя файла без расширения
        return base_name.lower()
        
    def parse_rules_file(self, file_type: str = "round") -> RulesFile:
        """Парсинг файла правил"""
        try:
            # Проверяем существование типа файла
            if file_type not in self.rules_files:
                # Перезагружаем файлы, возможно были добавлены новые
                self.load_rule_files()
                
                # Проверяем снова
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
                # Перезагружаем файлы, возможно были добавлены новые
                self.load_rule_files()
                
                # Проверяем снова
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
        # Перезагружаем список файлов перед выдачей результатов
        self.load_rule_files()
        
        # Формируем словарь с типами и отображаемыми именами
        result = {}
        for rule_type, file_path in self.rules_files.items():
            # Получаем имя файла для отображения
            file_name = os.path.basename(file_path)
            # Форматируем отображаемое имя
            display_name = f"Правила для {rule_type} элементов"
            result[rule_type] = display_name
            
        return result

    def create_new_rule_block(self, file_type: str, title: str, content: str) -> Optional[RuleBlock]:
        """Создание нового блока правил"""
        try:
            # Проверяем существование типа файла
            if file_type not in self.rules_files:
                # Перезагружаем файлы для актуализации списка
                self.load_rule_files()
                
                # Проверяем снова
                if file_type not in self.rules_files:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Неизвестный тип файла правил: {file_type}. Доступные типы: {', '.join(self.rules_files.keys())}"
                    )
            
            # Получаем текущие правила
            rules_file = self.parse_rules_file(file_type)
            
            # Генерируем ID для нового блока
            content_hash = hashlib.md5((title + content).encode('utf-8')).hexdigest()
            new_id = f"rule-{file_type}-{content_hash}"
            
            # Создаем новый блок
            new_block = RuleBlock(
                id=new_id,
                title=title,
                content=content
            )
            
            # Добавляем в список блоков
            rules_file.blocks.append(new_block)
            
            # Сохраняем изменения
            success = self.save_rules_file(file_type, rules_file)
            
            if success:
                return new_block
            
            return None
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при создании нового блока правил: {str(e)}"
            )
    
    def create_new_rules_file(self, file_type: str, file_name: str) -> bool:
        """Создание нового файла правил"""
        try:
            # Проверяем, что такого типа еще нет
            if file_type in self.rules_files:
                # Перезагружаем файлы для актуализации списка
                self.load_rule_files()
                
                # Проверяем снова
                if file_type in self.rules_files:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Тип файла правил '{file_type}' уже существует"
                    )
            
            # Добавляем расширение .txt, если оно отсутствует
            if not file_name.endswith('.txt'):
                file_name += '.txt'
                
            # Создаем путь к новому файлу
            file_path = os.path.join(self.rules_dir, file_name)
            
            # Создаем пустой файл
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"{self.title_separator}\nНовый блок правил\n{self.title_separator}\nСодержимое нового блока правил\n\n{self.block_separator}")
            
            # Добавляем файл в словарь
            self.rules_files[file_type] = file_path
            
            return True
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при создании нового файла правил: {str(e)}"
            )
            
    def delete_rule_block(self, block_id: str) -> bool:
        """Удаление блока правил"""
        # ID имеет формат rule-{file_type}-{hash}
        parts = block_id.split('-', 2)
        if len(parts) < 3 or parts[0] != "rule":
            return False
            
        file_type = parts[1]
        
        # Получаем все правила из файла
        rules_file = self.parse_rules_file(file_type)
        
        # Ищем блок для удаления
        block_index = None
        for i, block in enumerate(rules_file.blocks):
            if block.id == block_id:
                block_index = i
                break
        
        if block_index is not None:
            # Удаляем блок
            rules_file.blocks.pop(block_index)
            
            # Сохраняем изменения
            return self.save_rules_file(file_type, rules_file)
        
        return False

# Создаем экземпляр сервиса
rules_service = RulesService() 