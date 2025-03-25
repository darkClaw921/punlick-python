import asyncio
import logging
from typing import List, Dict, Any

# Импортируем существующий сервис и новый валидатор
from price_list_service import PriceListService
from price_validator_service import PriceValidatorService

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integration.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("integration")

async def process_items_with_validation(
    items: List[Dict[str, Any]], 
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Обрабатывает товары с использованием обоих методов: поиск соответствий и валидация
    
    Args:
        items: Список товаров для обработки
        similarity_threshold: Порог сходства для поиска соответствий и валидации
        
    Returns:
        List[Dict]: Обработанные товары
    """
    try:
        logger.info(f"Начало обработки {len(items)} товаров")
        
        # Инициализируем оба сервиса
        price_service = PriceListService()
        validator_service = PriceValidatorService()
        
        # Сначала ищем соответствия в базе
        logger.info("Шаг 1: Поиск соответствий в векторной базе")
        enriched_items = await price_service.find_matching_items(items, similarity_threshold)
        
        # Затем применяем правила валидации и интегрируем результаты
        logger.info("Шаг 2: Применение правил валидации и интеграция результатов")
        final_items = await validator_service.integrate_with_matching_service(
            items, enriched_items, similarity_threshold
        )
        
        # Подводим итоги
        matched_count = sum(1 for item in final_items if item.get("matched", False))
        corrected_count = sum(1 for item in final_items if item.get("corrected", False))
        unchanged_count = len(items) - matched_count - corrected_count
        
        logger.info(
            f"Обработка завершена: "
            f"{matched_count} найдено в базе, "
            f"{corrected_count} исправлено по правилам, "
            f"{unchanged_count} осталось без изменений, "
            f"всего {len(items)} товаров"
        )
        
        return final_items
        
    except Exception as e:
        logger.error(f"Ошибка при обработке товаров: {str(e)}")
        return items

async def main():
    # Пример данных для обработки
    test_items = [
        {"Наименование": "Заглушка 400*300", "Количество": 5, "Цена": 1200},
        {"Наименование": "Воздуховод ПР 500*300 -1250 Оц.С/0,7/ [20]", "Количество": 3, "Цена": 2500},
        {"Наименование": "Отвод 150*150/150*150", "Количество": 2, "Цена": 950},
        {"Наименование": "Отвод ПР 200*200-45° R150 Оц.С/0,5/ [20]", "Количество": 1, "Цена": 1800},
        {"Наименование": "Тройник 200*100/150*100/200*100", "Количество": 4, "Цена": 2100},
        {"Наименование": "Переход 500х300/300х200", "Количество": 2, "Цена": 1650}
    ]
    
    # Обрабатываем товары
    result = await process_items_with_validation(test_items, 0.7)
    
    # Выводим результаты
    print("\nРезультаты обработки:")
    print("-" * 80)
    
    for i, item in enumerate(result):
        original_name = item.get("Оригинальное_название", test_items[i]["Наименование"])
        current_name = item["Наименование"]
        
        if item.get("matched", False):
            status = "Найдено в базе ✓"
        elif item.get("corrected", False):
            status = "Исправлено по правилам ✓"
        else:
            status = "Без изменений"
            
        print(f"{i+1}. {status}")
        print(f"   Исходное:  {original_name}")
        print(f"   Итоговое:  {current_name}")
        print(f"   Цена: {item.get('Цена', 0)} | Кол-во: {item.get('Количество', 0)}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main()) 