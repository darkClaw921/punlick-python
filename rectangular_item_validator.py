import re
import logging
from typing import Dict, Any, Tuple, Optional, List, Pattern

class RectangularItemValidator:
    """Класс для валидации наименований прямоугольных элементов вентиляции"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Таблица толщины металла по размерам
        self.thickness_table = {
            300: 0.5,    # До 300 мм - 0.5 мм
            500: 0.7,    # От 300 до 500 мм - 0.7 мм
            800: 0.8,    # От 500 до 800 мм - 0.8 мм
            1000: 0.9,   # От 800 до 1000 мм - 0.9 мм
            float('inf'): 1.0  # Свыше 1000 мм - 1.0 мм
        }
        
        # Регулярные выражения для извлечения размеров
        self.re_dimensions = re.compile(r'(\d+)[*xх](\d+)')
        self.re_circular = re.compile(r'd\s*(\d+)')
        
    def validate_item(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Проверяет правильность наименования элемента вентиляции
        
        Args:
            item_name: Наименование элемента для проверки
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
                - Флаг валидности
                - Правильное наименование (если найдено)
                - Причина ошибки (если есть)
        """
        lower_name = item_name.lower()
        
        # Определение типа элемента
        if 'заглушка' in lower_name or 'глухарь' in lower_name or 'концевик' in lower_name or 'глушка' in lower_name:
            return self._validate_end_cap(item_name)
        elif 'воздуховод пр' in lower_name:
            return self._validate_duct(item_name)
        elif 'отвод' in lower_name or 'угол' in lower_name or 'колено' in lower_name:
            if 'r150' in lower_name or 'круглый' in lower_name or 'радиус' in lower_name:
                return self._validate_radius_elbow(item_name)
            else:
                return self._validate_corner_elbow(item_name)
        elif 'тройник' in lower_name:
            if 'кр врезкой' in lower_name or 'круглой врезкой' in lower_name:
                return self._validate_tee_with_circular(item_name)
            else:
                return self._validate_tee(item_name)
        elif 'переход' in lower_name:
            if ('на кр' in lower_name or 'на круглый' in lower_name or 
                self.re_circular.search(lower_name)):
                return self._validate_transition_to_circular(item_name)
            else:
                return self._validate_transition(item_name)
        elif 'врезка' in lower_name:
            if 'в площадку' in lower_name:
                return self._validate_insertion_plate(item_name)
            elif 'с отборт' in lower_name or 'с отбортовкой' in lower_name:
                return self._validate_insertion_flanged(item_name)
            else:
                return False, None, "Неизвестный тип врезки"
        elif 'зонт' in lower_name or 'козырек' in lower_name or 'навес' in lower_name:
            return self._validate_roof_hood(item_name)
        elif 'адаптер' in lower_name or 'пленум' in lower_name:
            return self._validate_adapter(item_name)
        elif 'дроссель' in lower_name:
            return self._validate_damper(item_name)
        elif 'обратный клапан' in lower_name:
            return self._validate_check_valve(item_name)
        elif 'шумоглушитель' in lower_name or 'глушитель' in lower_name:
            return self._validate_silencer(item_name)
        else:
            return False, None, "Неизвестный тип элемента"
    
    def _get_connection_type(self, dimensions: List[int]) -> str:
        """
        Определяет тип соединения в зависимости от размеров
        
        Args:
            dimensions: Список размеров элемента
            
        Returns:
            str: Тип соединения ([20], [30] и т.д.)
        """
        if any(dim >= 1000 for dim in dimensions):
            return "[30]"
        else:
            return "[20]"
    
    def _get_thickness(self, dimensions: List[int]) -> float:
        """
        Определяет толщину металла по таблице
        
        Args:
            dimensions: Список размеров элемента
            
        Returns:
            float: Толщина металла
        """
        max_dim = max(dimensions)
        
        for limit, thickness in sorted(self.thickness_table.items()):
            if max_dim <= limit:
                return thickness
                
        return 1.0  # Если все пороги превышены
    
    def _extract_dimensions(self, item_name: str) -> List[int]:
        """
        Извлекает размеры из наименования
        
        Args:
            item_name: Наименование элемента
            
        Returns:
            List[int]: Список размеров
        """
        dimensions = []
        matches = self.re_dimensions.findall(item_name)
        
        for width, height in matches:
            dimensions.append(int(width))
            dimensions.append(int(height))
            
        return dimensions
        
    def _validate_end_cap(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация заглушки ПР"""
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании заглушки"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Заглушка ПР {width}*{height} Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_duct(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация воздуховода ПР"""
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании воздуховода"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Воздуховод ПР {width}*{height} -1250 Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_corner_elbow(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация углового отвода ПР (без радиуса)"""
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании углового отвода"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        # Определение угла (по умолчанию 90°)
        angle = 90
        angle_match = re.search(r'[-–]\s*(\d+)[°º]', item_name)
        if angle_match:
            angle = int(angle_match.group(1))
            
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Отвод ПР {width}*{height}-{angle}° шейка 50*50 Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_radius_elbow(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация радиусного отвода ПР"""
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании радиусного отвода"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        # Определение угла (по умолчанию 90°)
        angle = 90
        angle_match = re.search(r'[-–]\s*(\d+)[°º]', item_name)
        if angle_match:
            angle = int(angle_match.group(1))
            
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Отвод ПР {width}*{height}-{angle}° R150 Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_tee(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация тройника ПР"""
        # Ищем все размеры в формате width*height
        all_dimensions = self.re_dimensions.findall(item_name)
        
        if len(all_dimensions) < 3:
            return False, None, "Недостаточно размеров в наименовании тройника (нужно 3 пары)"
            
        main_width, main_height = map(int, all_dimensions[0])
        branch_width, branch_height = map(int, all_dimensions[1])
        end_width, end_height = map(int, all_dimensions[2])
        
        dimensions = [main_width, main_height, branch_width, branch_height, end_width, end_height]
        
        # Длина тройника = первая ширина врезки + 200 мм
        length = branch_width + 200
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = (f"Тройник ПР {main_width}*{main_height}/{branch_width}*{branch_height}/"
                        f"{end_width}*{end_height} -{length} -100 Оц.С/{thickness}/ {connection}")
        
        return True, correct_name, None
        
    def _validate_tee_with_circular(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация тройника ПР с КР врезкой"""
        # Ищем размеры прямоугольной части
        rect_dimensions = self.re_dimensions.findall(item_name)
        
        if len(rect_dimensions) < 2:
            return False, None, "Недостаточно прямоугольных размеров в наименовании тройника с КР врезкой"
            
        main_width, main_height = map(int, rect_dimensions[0])
        end_width, end_height = map(int, rect_dimensions[1])
        
        # Ищем диаметр круглой врезки
        circular_match = self.re_circular.search(item_name)
        if not circular_match:
            return False, None, "Не найден диаметр круглой врезки"
            
        diameter = int(circular_match.group(1))
        
        dimensions = [main_width, main_height, end_width, end_height]
        
        # Длина тройника = диаметр круглой врезки + 200 мм
        length = diameter + 200
        
        thickness = self._get_thickness(dimensions)
        
        # Для тройника с КР врезкой соединение всегда 20-нп-20 или 30-нп-30
        if any(dim >= 1000 for dim in dimensions):
            connection = "[30-нп-30]"
        else:
            connection = "[20-нп-20]"
        
        correct_name = (f"Тройник ПР с КР врезкой {main_width}*{main_height}/d {diameter}/"
                        f"{end_width}*{end_height} -{length} -100 Оц.С/{thickness}/ {connection}")
        
        return True, correct_name, None
        
    def _validate_transition(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация перехода ПР"""
        # Ищем все размеры в формате width*height
        all_dimensions = self.re_dimensions.findall(item_name)
        
        if len(all_dimensions) < 2:
            return False, None, "Недостаточно размеров в наименовании перехода (нужно 2 пары)"
            
        start_width, start_height = map(int, all_dimensions[0])
        end_width, end_height = map(int, all_dimensions[1])
        
        dimensions = [start_width, start_height, end_width, end_height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        # По умолчанию тип-1
        transition_type = "тип-1"
        
        # Стандартная длина перехода 300 мм
        length = 300
        
        correct_name = (f"Переход ПР {start_width}*{start_height}/{end_width}*{end_height} "
                        f"-{length} {transition_type} Оц.С/{thickness}/ {connection}")
        
        return True, correct_name, None
        
    def _validate_transition_to_circular(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация перехода с ПР на КР"""
        # Ищем размеры прямоугольной части
        rect_match = self.re_dimensions.search(item_name)
        
        if not rect_match:
            return False, None, "Не найдены прямоугольные размеры в наименовании перехода с ПР на КР"
            
        rect_width, rect_height = map(int, rect_match.groups())
        
        # Ищем диаметр круглой части
        circular_match = self.re_circular.search(item_name)
        if not circular_match:
            # Если не нашли через d, ищем просто число
            circular_match = re.search(r'[/\\](\d+)(?!\d*[*xх])', item_name)
            if not circular_match:
                return False, None, "Не найден диаметр круглой части"
                
        diameter = int(circular_match.group(1))
        
        dimensions = [rect_width, rect_height]
        
        thickness = self._get_thickness(dimensions)
        
        # Для перехода с ПР на КР соединение всегда 20-нп или 30-нп
        if any(dim >= 1000 for dim in dimensions):
            connection = "[30-нп]"
        else:
            connection = "[20-нп]"
        
        # По умолчанию тип-1
        transition_type = "тип-1"
        
        # Стандартная длина перехода 300 мм
        length = 300
        
        correct_name = (f"Переход с ПР на КР {rect_width}*{rect_height}/d {diameter} "
                        f"-{length} {transition_type} Оц.С/{thickness}/ {connection}")
        
        return True, correct_name, None
        
    def _validate_insertion_plate(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация врезки ПР в площадку"""
        # Ищем размеры врезки
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании врезки в площадку"
            
        width, height = map(int, dimensions_match.groups())
        
        # Размер площадки = размер врезки + 50 мм по каждой стороне
        plate_width = width + 50 * 2
        plate_height = height + 50 * 2
        
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        
        # Стандартная длина врезки 100 мм
        length = 100
        
        correct_name = (f"Врезка ПР {width}*{height} в площадку {plate_width}*{plate_height} "
                        f"-{length} Оц.С/{thickness}/")
        
        return True, correct_name, None
        
    def _validate_insertion_flanged(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация врезки с отбортовкой ПР"""
        # Ищем размеры врезки
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании врезки с отбортовкой"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        
        # Для врезки с отбортовкой соединение всегда [20]
        connection = "[20]"
        
        # Стандартная длина врезки 100 мм
        length = 100
        
        correct_name = f"Врезка с отборт ПР {width}*{height} -{length} Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_roof_hood(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация зонта крышного ПР"""
        # Ищем размеры
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании зонта крышного"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Зонт крышный ПР {width}*{height} Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_adapter(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация адаптера (пленума) ПР"""
        # Ищем размеры посадочного места
        rect_match = self.re_dimensions.search(item_name)
        
        if not rect_match:
            return False, None, "Не найдены размеры посадочного места в наименовании адаптера"
            
        width, height = map(int, rect_match.groups())
        
        # Ищем диаметр врезки
        circular_match = self.re_circular.search(item_name)
        if not circular_match:
            return False, None, "Не найден диаметр врезки в наименовании адаптера"
            
        diameter = int(circular_match.group(1))
        
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        
        # Стандартная высота адаптера 300 мм
        height_value = 300
        
        correct_name = (f"Адаптер ПР {width}*{height} -{height_value}(h) с врезкой d {diameter} "
                        f"Оц.С/{thickness}/")
        
        return True, correct_name, None
        
    def _validate_damper(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация дроссель-клапана ПР"""
        # Ищем размеры
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании дроссель-клапана"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Дроссель ПР {width}*{height} Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_check_valve(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация обратного клапана ПР"""
        # Ищем размеры
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании обратного клапана"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = f"Обратный клапан ПР {width}*{height} Оц.С/{thickness}/ {connection}"
        
        return True, correct_name, None
        
    def _validate_silencer(self, item_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Валидация шумоглушителя пластинчатого ПР"""
        # Ищем размеры
        dimensions_match = self.re_dimensions.search(item_name)
        
        if not dimensions_match:
            return False, None, "Не найдены размеры в наименовании шумоглушителя"
            
        width, height = map(int, dimensions_match.groups())
        dimensions = [width, height]
        
        # Ищем длину шумоглушителя
        length_match = re.search(r'[-–](\d+)', item_name)
        if not length_match:
            length_match = re.search(r'[/\\](\d+)(?!\d*[*xх])', item_name)
            
        if not length_match:
            return False, None, "Не найдена длина шумоглушителя"
            
        length = int(length_match.group(1))
        
        thickness = self._get_thickness(dimensions)
        connection = self._get_connection_type(dimensions)
        
        correct_name = (f"Шумоглушитель пластинчатый ПР {width}*{height} -{length} "
                        f"SoundTek Оц.С/{thickness}/ {connection}")
        
        return True, correct_name, None
    
    
class RectangularItemProcessor:
    """Класс для обработки и исправления наименований прямоугольных элементов вентиляции"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validator = RectangularItemValidator()
    
    async def process_items(self, items: List[Dict[str, Any]], correction_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Обрабатывает список товаров и исправляет их наименования согласно правилам
        
        Args:
            items: Список товаров для обработки
            correction_threshold: Минимальный порог сходства для замены (0.0-1.0)
            
        Returns:
            List[Dict]: Список с исправленными наименованиями
        """
        try:
            # Результирующий список
            processed_items = []
            
            self.logger.info(f"Начало обработки {len(items)} товаров с порогом {correction_threshold * 100}%")
            
            for idx, item in enumerate(items):
                # Получаем название товара
                item_name = item.get("Наименование", "")
                
                if not item_name:
                    self.logger.info(f"[Товар {idx+1}] Пустое наименование, пропускаем")
                    processed_items.append(item)
                    continue
                
                # Проверяем наименование по правилам
                is_valid, correct_name, error = self.validator.validate_item(item_name)
                
                if not is_valid:
                    self.logger.info(f"[Товар {idx+1}] Не удалось валидировать: '{item_name}'. Причина: {error}")
                    processed_items.append(item)
                    continue
                
                # Если наименование уже правильное, оставляем как есть
                if item_name == correct_name:
                    self.logger.info(f"[Товар {idx+1}] Наименование уже верное: '{item_name}'")
                    processed_items.append(item)
                    continue
                
                # Иначе исправляем наименование
                self.logger.info(
                    f"[Товар {idx+1}] Исправлено: '{item_name}' --> '{correct_name}'"
                )
                
                # Создаем копию товара
                corrected_item = item.copy()
                
                # Сохраняем оригинальное название
                original_name = corrected_item["Наименование"]
                
                # Обновляем данные товара
                corrected_item["Наименование"] = correct_name
                corrected_item["Оригинальное_название"] = original_name
                corrected_item["corrected"] = True
                
                # Добавляем исправленный элемент
                processed_items.append(corrected_item)
            
            # Подводим итоги обработки
            corrected_count = sum(1 for item in processed_items if item.get("corrected", False))
            self.logger.info(
                f"Завершена обработка элементов: исправлено {corrected_count} из {len(items)} товаров"
            )
            
            return processed_items
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке товаров: {str(e)}")
            # В случае ошибки возвращаем исходный список
            return items


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Примеры элементов для проверки
    test_items = [
        {"Наименование": "Заглушка 400*300"},
        {"Наименование": "Воздуховод ПР 500*300 -1250 Оц.С/0,7/ [20]"},
        {"Наименование": "Отвод 150*150/150*150"},
        {"Наименование": "Отвод ПР 200*200-45° R150 Оц.С/0,5/ [20]"},
        {"Наименование": "Тройник 200*100/150*100/200*100"},
        {"Наименование": "Переход 500х300/300х200"}
    ]
    
    # Создаем процессор
    processor = RectangularItemProcessor()
    
    # Проверяем отдельный элемент
    validator = RectangularItemValidator()
    for item in test_items:
        is_valid, correct_name, error = validator.validate_item(item["Наименование"])
        if is_valid:
            print(f"Исходное: {item['Наименование']}")
            print(f"Правильное: {correct_name}")
            print("-" * 50)
        else:
            print(f"Ошибка валидации {item['Наименование']}: {error}")
            print("-" * 50) 