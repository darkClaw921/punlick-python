import math
import pandas as pd

def get_thickness(width, height):
    max_side = max(width, height)
    if max_side <= 250:
        return '0.5'
    elif max_side <= 750:
        return '0.7'
    elif max_side <= 1000:
        return '0.9'
    else:
        return '1.0'

import math

import pandas as pd

def process_zaglushka_kr(size, thickness, quantity, unit):
    """ Обработка Заглушек КР """

    # Извлекаем диаметр (например, d 100 → 100)
    kr_diameter = int(size.replace('d', '').strip())

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None" or thickness == "":
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')
    
    # Всегда заменяем точку на запятую
    thickness = thickness.replace('.', ',')

    # Проверяем, если unit пустой, то ставим "шт"
    if pd.isna(unit) or unit.strip() == "":
        unit = "шт"

    # Генерируем итоговое имя
    name = f"Заглушка КР d {kr_diameter} Оц.С/{thickness}/"

    return (name, quantity, unit)


def process_nippel(size, thickness, quantity, unit):
    """ Обработка Ниппелей (круглых соединителей) """

    # Извлекаем диаметр (например, d 100 → 100)
    kr_diameter = int(size.replace('d', '').strip())

    # Длина фиксированная 100 мм
    length = 100  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')

    # Генерируем итоговое имя
    name = f"Ниппель d {kr_diameter} -{length} Оц.С/{thickness.replace('.', ',')}/"

    return (name, quantity, unit)



def process_drossel_kr(size, thickness, quantity, unit):
    """ Обработка дроссель-клапанов КР """

    # Извлекаем диаметр (d 100, d 125, d 160, d 250, d 315)
    kr_diameter = int(size.replace('d', '').strip())

    # Определяем производителя
    manufacturer = "ГАЛВЕНТ" if kr_diameter <= 160 else "ВИНТЭЛ"

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')

    # Формируем итоговое наименование
    name = f"Дроссель-клапан КР d {kr_diameter} Оц.С/{thickness.replace('.', ',')}/ [нп] {manufacturer}"
    
    return (name, quantity, unit)


def process_drossel_pr(size, thickness, quantity, unit):
    """ Обработка дроссель-клапанов ПР """

    # Разбиваем размер (например, "250*250")
    width, height = map(int, size.replace('x', '*').split('*'))

    # Определяем соединение
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(width, height)
    else:
        thickness = str(thickness).replace(',', '.')

    # Генерируем итоговое имя
    name = f"Дроссель ПР {width}*{height} Оц.С/{thickness.replace('.', ',')}/ {connection}"
    
    return (name, quantity, unit)


def process_troynik_kr(size, thickness, quantity, unit):
    """ Обработка круглых тройников КР """

    # Разбиваем размеры (например, "160/125")
    diameters = list(map(int, size.split('/')))

    # Проверяем, что у тройника два диаметра (основной и врезка)
    if len(diameters) != 2:
        raise ValueError(f"Ошибка в размере тройника КР: {size}")

    # Основной диаметр и врезка
    d_main, d_branch = diameters

    # Переворачиваем, если врезка больше основного диаметра
    if d_branch > d_main:
        d_main, d_branch = d_branch, d_main  

    # Выходной диаметр такой же, как основной
    d_output = d_main  

    # Длина тройника = ширина врезки + 200
    length = d_branch + 200

    # Глубина врезки фиксированная
    depth = 100

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(d_main, d_main)
    else:
        thickness = str(thickness).replace(',', '.')

    # Генерируем итоговое имя
    name = f"Тройник КР d {d_main}/{d_branch}/{d_output} -{length} -{depth} Оц.С/{thickness.replace('.', ',')}/ [нп]"
    
    return (name, quantity, unit)


def process_troynik_pr(size, thickness, quantity, unit):
    """ Обработка полностью прямоугольных тройников ПР """

    # Разбиваем размеры (например, "500*250/250*250")
    size_parts = size.split("/")
    if len(size_parts) != 2:
        raise ValueError(f"Ошибка в размере тройника: {size}")

    # Основной канал (вход)
    input_width, input_height = map(int, size_parts[0].split('*'))

    # Врезка (боковой выход)
    branch_width, branch_height = map(int, size_parts[1].split('*'))

    # Выходной канал такой же, как входной
    output_width, output_height = input_width, input_height  

    # Длина тройника = ширина врезки + 200
    length = branch_width + 200  

    # Глубина врезки всегда фиксированная
    depth = 100  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(input_width, input_height)
    else:
        thickness = str(thickness).replace(',', '.')

    # Определяем соединение
    connection = "[30]" if max(input_width, input_height, branch_width, branch_height) >= 1000 else "[20]"

    # Генерируем итоговое имя
    name = f"Тройник ПР {input_width}*{input_height}/{branch_width}*{branch_height}/{output_width}*{output_height} -{length} -{depth} Оц.С/{thickness.replace('.', ',')}/ {connection}"
    
    return (name, quantity, unit)


def process_perehod_kr(size, thickness, quantity, unit, transition_type):
    """ Обработка Переходов КР (круглых переходов) """

    # Разбиваем размер (например, "100/125")
    diameters = list(map(int, size.split('/')))

    # Переворачиваем, если надо (меньший диаметр первым)
    diameters.sort()
    d_small, d_large = diameters

    # Длина перехода всегда 300 мм
    length = 300  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(d_large, d_large)
    else:
        thickness = str(thickness).replace(',', '.')

    # Генерируем итоговое имя
    name = f"Переход КР d {d_small}/{d_large} -{length} {transition_type} Оц.С/{thickness.replace('.', ',')}/ [нп]"
    
    return (name, quantity, unit)

def process_perehod_pr(size, thickness, quantity, unit, transition_type):
    """ Обработка Переходов ПР (прямоугольных переходов) """

    # Разбиваем размеры на верхнюю и нижнюю часть
    parts = size.split("/")
    if len(parts) != 2:
        raise ValueError(f"Ошибка в размере перехода: {size}")

    # Разделяем ширину и высоту
    width_top, height_top = map(int, parts[0].split('*'))
    width_bottom, height_bottom = map(int, parts[1].split('*'))

    # Длина перехода всегда 300 мм
    length = 300  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        max_side = max(width_top, height_top, width_bottom, height_bottom)
        thickness = get_thickness(max_side, max_side)
    else:
        thickness = str(thickness).replace(',', '.')

    # Определяем соединение
    connection = "[30]" if max(width_top, height_top, width_bottom, height_bottom) >= 1000 else "[20]"

    # **Исправлено**: Теперь добавляем `transition_type` в финальное название
    name = f"Переход ПР {width_top}*{height_top}/{width_bottom}*{height_bottom} -{length} {transition_type} Оц.С/{thickness.replace('.', ',')}/ {connection}"
    
    return (name, quantity, unit)


def process_spiralka_kr(size, thickness, quantity, unit):
    """ Обработка Спиралок КР (круглых спиральных воздуховодов) """

    # Приводим size к строке и убираем 'd'
    size_str = str(size).strip()
    kr_diameter = int(size_str.replace('d', ''))  

    # Длина всегда 3000
    standard_length = 3000  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')

    # ✅ Гарантируем, что `quantity` — это число
    try:
        quantity = float(quantity)
    except ValueError:
        quantity = 0  # Если не число, ставим 0, чтобы не сломалось

    # Пересчитываем п.м. в шт **ТОЛЬКО ЕСЛИ** ед. изм. - п.м.
    if str(unit).lower() in ["пм", "метры", "м"] and quantity > 0:
        quantity = math.ceil((quantity * 1000) / standard_length)  # ✅ Исправленный расчёт!
        unit_out = "шт"
    else:
        unit_out = unit

    # Формируем итоговое название
    name = f"Спиралка КР d {kr_diameter} -{standard_length} Оц.С/{thickness.replace('.', ',')}/ [нп]"
    
    return (name, quantity, unit_out)



def process_perehod_pr_kr(size, thickness, quantity, unit, transition_type):
    """ Обработка перехода с ПР на КР """
    
    # Разбираем размеры: основная часть (прямоугольник) и выход (круг)
    size_parts = size.split("/")
    width, height = map(int, size_parts[0].split('*'))  
    kr_diameter = int(size_parts[1].replace('d', ''))  

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(width, height)
    else:
        thickness = str(thickness).replace(',', '.')  # Убираем возможные запятые

    # Определяем соединение [20] / [30]
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    # Формируем итоговое название
    name = f"Переход с ПР на КР {width}*{height}/d {kr_diameter} -300 {transition_type} Оц.С/{thickness.replace('.', ',')}/ {connection}"
    
    return (name, quantity, "шт")


def process_otvod_pr(size, thickness, quantity, unit, angle):
    """ Обработка Отводов ПР (прямоугольных) """
    
    # Разбираем ширину и высоту
    size_parts = size.split('*')
    width, height = map(int, size_parts)  
    
    # Приводим угол к целому числу
    angle = int(round(float(angle)))

    # Если толщина не указана, подбираем по таблице
    if pd.isna(thickness) or thickness == "None":
        thickness = get_thickness(width, height)
    else:
        thickness = str(thickness).replace(',', '.')  # Убираем возможные запятые

    # Определяем соединение [20] или [30]
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    # Формируем итоговое название
    name = f"Отвод ПР {width}*{height}-{angle}° шейка 50*50 Оц.С/{thickness.replace('.', ',')}/ {connection}"
    
    return (name, quantity, "шт")

def process_vozduh_pr(size, thickness, quantity, unit):
    width, height = map(int, size.split('*'))
    if pd.isna(thickness):
        thickness = get_thickness(width, height)
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"
    unit = unit.upper().strip()
    if unit == "ПМ":
        quantity = math.ceil(quantity * 1000 / 1250)
        unit_out = "шт"
    else:
        unit_out = unit
    name = f"Воздуховод ПР {width}*{height} -1250 Оц.С/{str(thickness).replace('.', ',')}/ {connection}"
    return (name, quantity, unit_out)

import math

def process_troynik_pr_kr(size, thickness, quantity, unit):
    """ Обработка Тройников ПР с круглой врезкой """

    # Разбиваем строку "250*250/d160"
    size_parts = size.split("/")
    width, height = map(int, size_parts[0].split('*'))  # 250*250 → width=250, height=250
    kr_diameter = int(size_parts[1].replace('d', ''))  # Убираем 'd', получаем 160

    # Добавляем пробел после `d`
    kr_diameter_str = f"d {kr_diameter}"

    # Выходной размер (он такой же, как входной)
    output_width, output_height = width, height  

    # Длина = диаметр + 200
    length = kr_diameter + 200  
    depth = 100  # Фиксированная глубина

    # Определяем толщину
    if pd.isna(thickness):
        thickness = get_thickness(width, height)

    # Определяем соединение
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    # Формируем итоговое название
    name = (
        f"Тройник ПР с КР врезкой {width}*{height}/{kr_diameter_str}/{output_width}*{output_height} "
        f"-{length} -{depth} Оц.С/{str(thickness).replace('.', ',')}/ {connection}"
    )
    
    return (name, quantity, unit)


def process_otvod_kr(size, thickness, quantity, unit, angle):
    kr_diameter = int(size.replace('d', ''))  # Убираем 'd'
    
    # Приводим угол к целому числу
    angle = int(round(float(angle)))  

    # Определяем тип и толщину
    if kr_diameter <= 125:
        type_ = "ГАЛВЕНТ"
        # Для d<=125 толщина по таблице (0.5) если не указана
        if pd.isna(thickness):
            thickness = get_thickness(kr_diameter, kr_diameter)
        else:
            thickness = str(thickness).replace(',', '.')  # На случай если в данных запятая
    elif kr_diameter == 160:
        if angle == 90:
            type_ = "ГАЛВЕНТ"
            thickness = '0.9'  # Исключение
        elif angle == 45:
            type_ = "ВИНТЭЛ"
            if pd.isna(thickness):
                thickness = get_thickness(kr_diameter, kr_diameter)
            else:
                thickness = str(thickness).replace(',', '.')
        else:
            raise ValueError(f"Неподдерживаемый угол для d160: {angle}°")
    else:
        type_ = "ВИНТЭЛ"
        if pd.isna(thickness):
            thickness = get_thickness(kr_diameter, kr_diameter)
        else:
            thickness = str(thickness).replace(',', '.')

    # Формируем имя с пробелом после "d"
    name = (
        f"Отвод КР d {kr_diameter}-{angle}° R-150 Оц.С/{thickness.replace('.', ',')}/ [нп] {type_}"
    )
    
    return (name, quantity, "шт")

def convert_to_final_format(row):
    """ Определяет тип изделия и вызывает нужную функцию """
    item_type, size, thickness, quantity, unit, angle, transition_type = row  # Теперь есть "Тип"!

    if "Воздуховод ПР" in item_type:
        return process_vozduh_pr(size, thickness, quantity, unit)
    elif "Тройник ПР с КР врезкой" in item_type:
        return process_troynik_pr_kr(size, thickness, quantity, unit)
    elif "Отвод КР" in item_type:
        return process_otvod_kr(size, thickness, quantity, unit, angle)
    elif "Отвод ПР" in item_type:
        return process_otvod_pr(size, thickness, quantity, unit, angle)
    elif "Переход с ПР на КР" in item_type:
        return process_perehod_pr_kr(size, thickness, quantity, unit, transition_type)
    elif "Спиралка КР" in item_type:
        return process_spiralka_kr(size, thickness, quantity, unit)
    elif "Переход ПР" in item_type:
        return process_perehod_pr(size, thickness, quantity, unit, transition_type)  # ✅ Теперь передаём transition_type
    elif "Переход КР" in item_type:
        return process_perehod_kr(size, thickness, quantity, unit, transition_type)
    elif "Тройник ПР" in item_type:
        return process_troynik_pr(size, thickness, quantity, unit)
    elif "Тройник КР" in item_type:
        return process_troynik_kr(size, thickness, quantity, unit)
    elif "Дроссель ПР" in item_type or "Регулирующий клапан" in item_type or "Клапан дроссельный" in item_type:
        return process_drossel_pr(size, thickness, quantity, unit)
    elif "Дроссель-клапан КР" in item_type or "Дроссель" in item_type or "Клапан дроссельный" in item_type or "Дроссельная заслонка" in item_type:
        return process_drossel_kr(size, thickness, quantity, unit)
    elif "Ниппель" in item_type:
        return process_nippel(size, thickness, quantity, unit)
    elif "Заглушка КР" in item_type:
        return process_zaglushka_kr(size, thickness, quantity, unit)

    else:
        return (item_type, quantity, unit)  # Если тип неизвестен, возвращаем как есть




test_data =[
    {
        "Наименование": "Отвертка Φ100",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Врезка Φ125/Φ200",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Отвертка Φ160",
        "Количество": "4 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Переход Φ315/Φ250",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Отвертка Φ250",
        "Количество": "2 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Дроссель Φ160",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Отвертка Φ200",
        "Количество": "3 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Воздуховод 450*350",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Воздуховод Φ250",
        "Количество": "4 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Воздуховод Φ200",
        "Количество": "4 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Воздуховод Φ160",
        "Количество": "2 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Отвертка 45° Φ250",
        "Количество": "6 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Заглушка Φ200",
        "Количество": "2 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Заглушка Φ250",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Врезка Φ200/Φ200",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Дроссель Φ125",
        "Количество": "3 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Врезка Φ125/Φ160",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Отвертка 45° Φ100",
        "Количество": "2 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Переход Φ125/Φ160",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Где просто отвертка - 3то 90°",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    },
    {
        "Наименование": "Один ТАКОЙ переход",
        "Количество": "1 шт",
        "Ед.изм.": "шт"
    }
]
# Чтение и запись
# df_input = pd.read_excel("ЗАЯВКА.xlsx")  
df_input = pd.DataFrame(test_data)
# df_input.columns = ["Наименование", "Размер", "Толщина", "Кол-во", "Ед. изм.", "Угол", "Тип"]  # Теперь 7 колонок!
df_input.columns = ["Наименование", "Количество", "Ед.изм."]

df_output = df_input.apply(convert_to_final_format, axis=1, result_type="expand")
df_output.columns = ["Наименование", "Количество", "Ед.изм."]
df_output.to_excel("РЕЗУЛЬТАТ.xlsx", index=False)
print("✅ Готово!")