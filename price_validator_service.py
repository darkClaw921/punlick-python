import logging
from typing import List, Dict, Any, Optional
from rectangular_item_validator import RectangularItemValidator, RectangularItemProcessor

class PriceValidatorService:
    """Сервис для проверки и валидации прайс-листов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rect_validator = RectangularItemValidator()
        self.rect_processor = RectangularItemProcessor()
        
    async def validate_and_correct_items(self, items: List[Dict[str, Any]], 
                                        similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Проверяет и исправляет наименования товаров согласно правилам
        
        Args:
            items: Список товаров для обработки
            similarity_threshold: Минимальный порог сходства для применения исправлений
            
        Returns:
            List[Dict]: Список обработанных товаров
        """
        try:
            # Сначала обрабатываем прямоугольные элементы
            processed_items = await self.rect_processor.process_items(items, similarity_threshold)
            
            # Здесь можно добавить обработку других типов элементов
            # ...
            
            return processed_items
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации и исправлении товаров: {str(e)}")
            return items
    
    async def integrate_with_matching_service(self, items: List[Dict[str, Any]], 
                                            enriched_items: List[Dict[str, Any]],
                                            similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Интегрирует результаты поиска соответствий с результатами валидации
        
        Args:
            items: Исходные товары
            enriched_items: Товары, обогащенные сервисом поиска соответствий
            similarity_threshold: Порог схожести для принятия коррекции
            
        Returns:
            List[Dict]: Итоговый список обработанных товаров
        """
        try:
            result_items = []
            
            self.logger.info(f"Начало интеграции результатов для {len(items)} товаров")
            
            for idx, (orig_item, enriched_item) in enumerate(zip(items, enriched_items)):
                # Если наименование уже заменено через поиск соответствий
                if enriched_item.get("matched", False):
                    self.logger.info(
                        f"[Товар {idx+1}] Применяем замену по соответствию: "
                        f"'{orig_item.get('Наименование', '')}' -> '{enriched_item.get('Наименование', '')}'"
                    )
                    result_items.append(enriched_item)
                    continue
                    
                # Если соответствие не найдено, пытаемся исправить по правилам
                item_name = enriched_item.get("Наименование", "")
                
                if not item_name:
                    result_items.append(enriched_item)
                    continue
                    
                # Проверяем наименование по правилам
                is_valid, correct_name, error = self.rect_validator.validate_item(item_name)
                
                if not is_valid:
                    self.logger.info(
                        f"[Товар {idx+1}] Не удалось валидировать: '{item_name}'. "
                        f"Оставляем исходное наименование."
                    )
                    result_items.append(enriched_item)
                    continue
                
                # Если наименование уже правильное, оставляем как есть
                if item_name == correct_name:
                    self.logger.info(f"[Товар {idx+1}] Наименование уже верное: '{item_name}'")
                    result_items.append(enriched_item)
                    continue
                
                # Иначе исправляем наименование
                self.logger.info(
                    f"[Товар {idx+1}] Исправляем по правилам: '{item_name}' --> '{correct_name}'"
                )
                
                # Создаем копию товара
                corrected_item = enriched_item.copy()
                
                # Сохраняем оригинальное название
                original_name = item_name
                
                # Обновляем данные товара
                corrected_item["Наименование"] = correct_name
                corrected_item["Оригинальное_название"] = original_name
                corrected_item["corrected"] = True
                
                # Добавляем исправленный элемент
                result_items.append(corrected_item)
            
            # Подводим итоги обработки
            matched_count = sum(1 for item in result_items if item.get("matched", False))
            corrected_count = sum(1 for item in result_items if item.get("corrected", False))
            
            self.logger.info(
                f"Завершена интеграция результатов: "
                f"{matched_count} соответствий в базе, {corrected_count} исправлено по правилам, "
                f"всего {len(items)} товаров"
            )
            
            return result_items
            
        except Exception as e:
            self.logger.error(f"Ошибка при интеграции результатов: {str(e)}")
            return enriched_items


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Примеры элементов для проверки
    # переход φ125/φ160
    test_items = [
        {"Наименование": "переход с пр на кр 160*125/d 125 -300 тип-1 оц.с/0,5/ [20-нп], шт"},
        {"Наименование": "переход φ125/φ160"},
        {"Наименование": "врезка кр в кр трубу d 125/160 -150 оц.с/0,5/, шт"},
        # {"Наименование": "Отвод ПР 200*200-45° R150 Оц.С/0,5/ [20]"},
        # {"Наименование": "Тройник 200*100/150*100/200*100"},
        # {"Наименование": "Переход 500х300/300х200"}
    ]
    
    # Создаем сервис
    validator_service = PriceValidatorService()
    
    # Проверяем элементы
    import asyncio
    
    async def test():
        result = await validator_service.validate_and_correct_items(test_items)
        
        for i, item in enumerate(result):
            print(f"{i+1}. Исходное: {test_items[i]['Наименование']}")
            print(f"   Исправленное: {item['Наименование']}")
            print("-" * 50)
    
    asyncio.run(test()) 