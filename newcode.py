import math
import traceback
import numpy as np
import pandas as pd

def normalize_thickness(th):
    """Преобразует толщину: 0.55 → 0.5, 0.6 → 0.7 и заменяет точку на запятую"""
    if pd.isna(th) or str(th).strip().lower() in ["", "none", "nan"]:
        return th
    th = str(th).replace(',', '.').strip()
    if th == "0.55":
        th = "0.5"
    elif th == "0.6":
        th = "0.7"
    return th.replace('.', ',')


def process_skotch(row):
    """Обработка алюминиевого скотча ВИНТЭЛ 100х40м (упак 12 шт)."""
    quantity = int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1

    name = "Скотч алюминиевый ВИНТЭЛ 100х40м (упак 12 шт)"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": "шт"
    }

def process_diffuzor(row):
    size = str(row["Размер"]).strip().lower().replace('x', 'х')  # <-- русская "х" везде
    
    quantity = 1 if row['Кол-во']=='-' else int(float(str(row["Кол-во"]).replace(',', '.')))
    unit = row["Ед. изм."] if not pd.isna(row["Ед. изм."]) else "шт"

    if '450х450' in size:
        diffuzor_name = "Диффузор вентиляционный потолочный 4АПН (анемостат) 450х450 мм"
        adapter_name = "Адаптер ПР 300*300 -300(h) с врезкой d 200 Оц.С/0,5/"
    elif '600х600' in size:
        diffuzor_name = "Диффузор вентиляционный потолочный 4АПН (анемостат) 600х600 мм"
        adapter_name = "Адаптер ПР 460*460 -300(h) с врезкой d 200 Оц.С/0,5/"
    else:
        diffuzor_name = f"Диффузор вентиляционный потолочный 4АПН (анемостат) {size} мм"
        size_adapter = size.replace('х', '*').replace('x', '*')  # если пользователь ввёл что-то иное
        adapter_name = f"Адаптер ПР {size_adapter} -300(h) с врезкой d 200 Оц.С/0,5/"

    return [
        {
            "Наименование": diffuzor_name,
            "Кол-во": quantity,
            "Ед. изм.": unit
        },
        {
            "Наименование": adapter_name,
            "Кол-во": quantity,
            "Ед. изм.": unit
        }
    ]



def process_perehod(row):
    size_raw = str(row["Размер"]).replace("х", "x").replace("*", "x").replace(" ", "").lower()
    parts = size_raw.split("/")
    if len(parts) != 2:
        raise ValueError(f"⛔ Неверный формат размера перехода: {size_raw}")

    def is_rect(part): return 'x' in part
    def is_round(part): return not is_rect(part)

    part1, part2 = parts

    def parse_rect(s):
        w, h = map(int, s.split("x"))
        return w, h

    def parse_dia(s):
        return int(s.replace('d', '').replace('ø', '').replace('ф', ''))

    # Тип (учёт "-" как отсутствующего значения, защита от "тип-тип-1")
    raw_type = str(row["Тип"]).strip().lower()
    if raw_type in ["", "none", "nan", "-"]:
        raw_type = "1"
    if not raw_type.startswith("тип-"):
        transition_type = f"тип-{raw_type}"
    else:
        transition_type = raw_type

    # Переход КР ↔ КР
    if is_round(part1) and is_round(part2):
        d1, d2 = sorted([parse_dia(part1), parse_dia(part2)])
        thickness = row["Толщина"]
        if pd.isna(thickness) or str(thickness).strip().lower() in ["", "none", "nan"]:
            thickness = get_thickness(d2, d2)
        else:
            thickness = str(thickness).replace(',', '.')
        thickness = thickness.replace('.', ',')

        name = f"Переход КР d {d1}/{d2} -300 {transition_type} Оц.С/{thickness}/ [нп]"

    # Переход ПР ↔ ПР
    elif is_rect(part1) and is_rect(part2):
        w1, h1 = parse_rect(part1)
        w2, h2 = parse_rect(part2)
        thickness = row["Толщина"]
        if pd.isna(thickness) or str(thickness).strip().lower() in ["", "none", "nan"]:
            thickness = get_thickness(w1, h1)
        else:
            thickness = str(thickness).replace(',', '.')
        thickness = thickness.replace('.', ',')

        connection = "[30]" if max(w1, h1, w2, h2) >= 1000 else "[20]"
        name = f"Переход ПР {w1}*{h1}/{w2}*{h2} -300 {transition_type} Оц.С/{thickness}/ {connection}"

    # Переход с ПР на КР
    else:
        if is_rect(part1):
            width, height = parse_rect(part1)
            dia = parse_dia(part2)
        else:
            width, height = parse_rect(part2)
            dia = parse_dia(part1)
        thickness = row["Толщина"]
        if pd.isna(thickness) or str(thickness).strip().lower() in ["", "none", "nan"]:
            thickness = get_thickness(width, height)
        else:
            thickness = str(thickness).replace(',', '.')
        thickness = thickness.replace('.', ',')

        connection = "[30]" if max(width, height) >= 1000 else "[20]"
        name = f"Переход с ПР на КР {width}*{height}/d {dia} -300 {transition_type} Оц.С/{thickness}/ {connection}"

    quantity = int(float(row["Кол-во"])) if pd.notna(row["Кол-во"]) else 1
    unit = row["Ед. изм."] if pd.notna(row["Ед. изм."]) and str(row["Ед. изм."]).strip() else "шт"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": unit
    }



def process_vrezka(row):
    """Универсальный обработчик всех типов врезок: КР/КР, ПР/КР, с отбортовкой"""
    size = str(row["Размер"]).strip().lower()
    size = size.replace('d', '').replace('ф', '').replace('ø', '').replace(' ', '')

    mark = "-100 Оц.С"
    thickness = row["Толщина"]
    if pd.isna(thickness):
        thickness = "0.5"
    thickness = normalize_thickness(thickness)

    if '/' in size:
        part1, part2 = size.split('/')

        # Прямоугольная врезка в круглую трубу
        if any(x in part1 for x in ['x', 'х', '*']):
            pr_part = part1.replace('х', '*').replace('x', '*')
            width, height = map(int, pr_part.split('*'))
            diameter = int(part2)
            connection = "[30]" if max(width, height) >= 1000 else "[20]"
            name = f"Врезка ПР в КР трубу {width}*{height}/d {diameter} {mark}/{thickness}/ {connection}"
        else:
            # Круглая врезка в круглую трубу
            d1, d2 = map(int, [part1, part2])
            name = f"Врезка КР в КР трубу d {min(d1,d2)}/{max(d1,d2)} {mark}/{thickness}/"
    else:
        # Врезка с отбортовкой
        if any(x in size for x in ['x', 'х', '*']):
            size = size.replace('х', '*').replace('x', '*')
            width, height = map(int, size.split('*'))
            connection = "[30]" if max(width, height) >= 1000 else "[20]"
            name = f"Врезка с отборт ПР {width}*{height} {mark}/{thickness}/ {connection}"
        else:
            diameter = int(size)
            name = f"Врезка с отборт КР d {diameter} {mark}/{thickness}/"
    count = 1 if row['Кол-во']=='-' else int(float(str(row["Кол-во"]).replace(',', '.')))
    return {
        "Наименование": name,
        "Кол-во": count,
        "Ед. изм.": row["Ед. изм."] if pd.notna(row["Ед. изм."]) else "шт"
    }

def process_ozks(row):
    """Обработка огнезащитного состава ОЗКС, фасовка 25кг, округляется по вёдрам (шт)."""
    requested_kg = float(str(row["Кол-во"]).replace(',', '.')) if not pd.isna(row["Кол-во"]) else 0
    buckets = math.ceil(requested_kg / 25)  # количество ведер
    name = 'Огнезащитный состав "ОЗКС" (25кг) серый'

    return {
        "Наименование": name,
        "Кол-во": buckets,
        "Ед. изм.": "шт"
    }

def process_troynik(row):
    size = str(row["Размер"]).lower().replace("х", "x").replace("*", "x").replace(" ", "")
    parts = size.split('/')

    quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
    unit = row["Ед. изм."] or "шт"

    # --- Тройник ПР с КР врезкой ---
    if len(parts) in [2, 3] and 'x' in parts[0] and 'x' not in parts[1]:
        w1, h1 = map(int, parts[0].split('x'))  # прямоугольный вход
        d_branch = int(re.sub(r'[^\d]', '', parts[1]))  # круглая врезка
        if len(parts) == 3 and 'x' in parts[2]:
            w3, h3 = map(int, parts[2].split('x'))
        else:
            w3, h3 = w1, h1

        length = d_branch + 200
        depth = 100
        thickness = row["Толщина"] or get_thickness(w1, h1)
        thickness = normalize_thickness(thickness)
        connection = "[30]" if max(w1, h1, w3, h3, d_branch) >= 1000 else "[20]"

        name = f"Тройник ПР с КР врезкой {w1}*{h1}/d {d_branch}/{w3}*{h3} -{length} -{depth} Оц.С/{thickness}/ {connection}"
        return {"Наименование": name, "Кол-во": quantity, "Ед. изм.": unit}

    size = str(row["Размер"]).lower().replace("х", "x").replace("*", "x").replace(" ", "")
    parts = size.split('/')

    # --- Круглый тройник ---
    if all('x' not in p for p in parts):
        diameters = list(map(int, [re.sub(r'[^\d]', '', p) for p in parts]))
        if len(diameters) == 1:
            d_main = d_branch = d_output = diameters[0]
        elif len(diameters) == 2:
            d1, d2 = diameters
            d_main, d_branch = max(d1, d2), min(d1, d2)
            d_output = d_main
        elif len(diameters) == 3:
            d_main, d_branch, d_output = diameters
        else:
            raise ValueError(f"⛔ Неверный формат тройника КР: {size}")
        
        length = d_branch + 200
        depth = 100
        thickness = row["Толщина"] or get_thickness(d_main, d_main)
        thickness = normalize_thickness(thickness)
        quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
        unit = row["Ед. изм."] or "шт"
        name = f"Тройник КР d {d_main}/{d_branch}/{d_output} -{length} -{depth} Оц.С/{thickness}/ [нп]"
        return {"Наименование": name, "Кол-во": quantity, "Ед. изм.": unit}

    # --- КР с ПР врезкой ---
    elif len(parts) == 2 and 'x' in parts[1] and 'x' not in parts[0]:
        kr_diameter = int(re.sub(r'[^\d]', '', parts[0]))
        width, height = map(int, parts[1].split('x'))
        d_out = kr_diameter
        length = width + 200
        depth = 100
        thickness = row["Толщина"] or get_thickness(width, height)
        thickness = normalize_thickness(thickness)
        quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
        unit = row["Ед. изм."] or "шт"
        name = f"Тройник КР с ПР врезкой d {kr_diameter}/{width}*{height}/d {d_out} -{length} -{depth} Оц.С/{thickness}/ [нп]"
        return {"Наименование": name, "Кол-во": quantity, "Ед. изм.": unit}

    # --- Прямоугольный тройник (формат вход/врезка/выход) ---
    elif len(parts) == 3 and all('x' in p for p in parts):
        w1, h1 = map(int, parts[0].split('x'))  # вход
        w2, h2 = map(int, parts[1].split('x'))  # врезка
        w3, h3 = map(int, parts[2].split('x'))  # выход
        length = w2 + 200
        depth = 100
        thickness = row["Толщина"] or get_thickness(w1, h1)
        thickness = normalize_thickness(thickness)
        quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
        unit = row["Ед. изм."] or "шт"
        connection = "[30]" if max(w1, h1, w2, h2, w3, h3) >= 1000 else "[20]"
        name = f"Тройник ПР {w1}*{h1}/{w2}*{h2}/{w3}*{h3} -{length} -{depth} Оц.С/{thickness}/ {connection}"
        return {"Наименование": name, "Кол-во": quantity, "Ед. изм.": unit}

    # --- Прямоугольный тройник (вход/врезка) ---
    elif len(parts) == 2 and all('x' in p for p in parts):
        w1, h1 = map(int, parts[0].split('x'))  # вход
        w2, h2 = map(int, parts[1].split('x'))  # врезка
        w3, h3 = w1, h1  # выход = вход
        if h2 > h1:  # поправка, если врезка больше
            w1, h1, w2, h2 = w2, h2, w1, h1
            w3, h3 = w1, h1
        length = w2 + 200
        depth = 100
        thickness = row["Толщина"] or get_thickness(w1, h1)
        thickness = normalize_thickness(thickness)
        quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
        unit = row["Ед. изм."] or "шт"
        connection = "[30]" if max(w1, h1, w2, h2) >= 1000 else "[20]"
        name = f"Тройник ПР {w1}*{h1}/{w2}*{h2}/{w3}*{h3} -{length} -{depth} Оц.С/{thickness}/ {connection}"
        return {"Наименование": name, "Кол-во": quantity, "Ед. изм.": unit}

    raise ValueError(f"⛔ Не удалось интерпретировать размер тройника: {size}")


def process_mbor(row):
    """Обработка изоляционного материала Бизол МБОР."""
    thickness = int(float(str(row["Толщина"]).replace(',', '.')))
    quantity = float(str(row["Кол-во"]).replace(',', '.')) if not pd.isna(row["Кол-во"]) else 1

    name = f"Теплоогнезащитное покрытие Бизол МБОР-{thickness}Ф 20000*1200*{thickness}мм"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": "м2"
    }


def process_penofol(row):
    """Обработка изоляции Пенофол с фиксированными параметрами рулона."""
    thickness = int(float(str(row["Толщина"]).replace(',', '.')))
    quantity = float(str(row["Кол-во"]).replace(',', '.')) if not pd.isna(row["Кол-во"]) else 1

    name = f"Изоляция Пенофол тип С {thickness}х600мм - 9 м2 - 15м.п"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": "м2"
    }


def process_regulyator_klapan(row):
    """Обработка обратных и воздушных клапанов по типу: RSK или КВК."""
    size = str(row["Размер"]).strip().lower().replace('d', '').replace('ф', '').replace('ø', '').replace('-', '')
    diameter = int(size)

    type_field = str(row["Тип"]).strip().upper()

    if "RSK" in type_field:
        name = f"Обратный клапан круглый RSK d {diameter} мм"
    elif "КВК" in type_field:
        name = f"Воздушный клапан КВ с площадкой и ручкой d {diameter} ГАЛВЕНТ"
    else:
        raise ValueError(f"⛔ Неизвестный тип регулирующего клапана: {type_field}")

    quantity = int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1
    unit = row["Ед. изм."] if not pd.isna(row["Ед. изм."]) else "шт"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": unit
    }


def process_shumoglushitel(row):
    """Обработка шумоглушителя (круглый и прямоугольный)."""
    size = str(row["Размер"]).strip().lower().replace('d', '').replace('ф', '').replace('ø', '')
    
    # Заменяем все возможные варианты символа 'x' на стандартный
    size = size.replace('х', 'x').replace('×', 'x')

    # Проверяем, является ли размер прямоугольным
    if 'x' in size:  # Прямоугольный
        try:
            width, height = map(int, size.split('x'))
        except ValueError:
            raise ValueError(f"Некорректный размер прямоугольного шумоглушителя: {size}")

        # Длина
        length = int(row["Длина"]) if not pd.isna(row["Длина"]) else 1000

        # Толщина по таблице
        thickness = str(row["Толщина"]).strip() if not pd.isna(row["Толщина"]) else ""
        if thickness in ["", "-", "None", "nan"]:  # Если толщина не указана или указан "-"
            thickness = get_thickness(width, height)  # Определение толщины по таблице
        else:
            thickness = thickness.replace(',', '.')
        thickness = thickness.replace('.', ',')

        # Кол-во
        quantity = int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1

        # Ед. изм.
        unit = row["Ед. изм."] if not pd.isna(row["Ед. изм."]) else "шт"

        # Определение соединения
        connection = "[30]" if max(width, height) >= 1000 else "[20]"

        name = f"Шумоглушитель пластинчатый ПР {width}*{height} -{length} SoundTek Оц.С/{thickness}/ {connection}"

        return {
            "Наименование": name,
            "Кол-во": quantity,
            "Ед. изм.": unit
        }
    
    else:  # Круглый
        try:
            diameter = int(size)
        except ValueError:
            raise ValueError(f"Некорректный размер круглого шумоглушителя: {size}")

        # Длина
        length = int(row["Длина"]) if not pd.isna(row["Длина"]) else 900

        # Толщина
        thickness = str(row["Толщина"]).strip() if not pd.isna(row["Толщина"]) else ""
        if thickness in ["", "-", "None", "nan"]:  # Если толщина не указана или указан "-"
            thickness = '0,5'  # Значение по умолчанию для круглых
        else:
            thickness = thickness.replace(',', '.')
            thickness = thickness.replace('.', ',')

        # Кол-во
        quantity = int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1

        # Ед. изм.
        unit = row["Ед. изм."] if not pd.isna(row["Ед. изм."]) else "шт"

        name = f"Шумоглушитель КР d {diameter} -{length} SoundTek Оц.С/{thickness}/"

        return {
            "Наименование": name,
            "Кол-во": quantity,
            "Ед. изм.": unit
        }


# ------------------- Толщина по таблице -------------------
def get_thickness(width, height):
    if pd.isna(width) or pd.isna(height):
        raise ValueError(f"CRITICAL ERROR! В get_thickness() переданы nan: width={width}, height={height}")
    max_side = max(width, height)
    if max_side <= 250:
        return '0.5'
    elif 300 <= max_side <= 1000:
        return '0.7'
    elif 1001 <= max_side <= 2000:
        return '0.9'
    else:
        return 'Ошибка: уточните параметры для данного размера'

def process_deflector(row):
    """Генерирует полное тех. название дефлектора с автоматическим подбором толщины"""
    # Очистка диаметра
    diameter = str(row["Размер"]).strip().lower()
    diameter = re.sub(r'[^\d]', '', diameter)  # Удаляем все нецифровые символы
    
    if not diameter:
        raise ValueError("Не удалось определить диаметр дефлектора")
    
    diameter_int = int(diameter)
    
    # Получаем толщину (аналогично process_nippel)
    if pd.isna(row["Толщина"]) or str(row["Толщина"]).strip() in ["", "None"]:
        # Для круглых дефлекторов используем диаметр как width и height
        thickness = get_thickness(diameter_int, diameter_int).replace('.', ',')
    else:
        thickness = str(row["Толщина"]).replace('.', ',')
    
    # Формирование итогового названия
    name = f"Дефлектор ЦАГИ d {diameter} Оц.С/{thickness}/ [нп]"
    
    return {
        "Наименование": name,
        "Размер": diameter,
        "Толщина": "",
        "Кол-во": int(row["Кол-во"]) if not pd.isna(row["Кол-во"]) else 1,
        "Ед. изм.": row.get("Ед. изм.", "шт"),
        "Угол": "",
        "Тип": "",
        "Длина": ""
    }


def process_nippel(row):
    """Генерирует полное техническое название ниппеля для заявки."""
    # Извлекаем диаметр (если введено "d100" или просто "100")
    diameter = str(row["Размер"]).strip().lower().replace('d', '').strip()
    
    # Фиксированная длина 100 мм
    length = 100
    
    # Обработка толщины
    if pd.isna(row["Толщина"]) or row["Толщина"] == "None":
        thickness = get_thickness(int(diameter), int(diameter)).replace('.', ',')
    else:
        thickness = str(row["Толщина"]).replace('.', ',')
    
    # Формируем итоговое название
    name = f"Ниппель d {diameter} -{length} Оц.С/{thickness}/"
    
    return {
        "Наименование": name,  # Полное техническое название
        "Кол-во": int(row["Кол-во"]) if not pd.isna(row["Кол-во"]) else 1,
        "Ед. изм.": row.get("Ед. изм.", "шт")
    }

def process_zaglushka(row):
    """Универсальная обработка заглушек (автоматически определяет ПР или КР)"""
    
    # Приводим размер к строке и очищаем
    size = str(row["Размер"]).lower().strip().replace("х", "x").replace("*", "x").replace(" ", "")
    
    # Определяем тип заглушки
    if 'x' in size:
        # Это заглушка ПР (прямоугольная)
        return process_zaglushka_pr(row)
    elif size.startswith('d') or size.replace('d', '').isdigit():
        # Это заглушка КР (круглая)
        return process_zaglushka_kr(row)
    else:
        # Пытаемся определить по числовым значениям (например, "315" - это d315)
        try:
            # Пробуем преобразовать в число - если получится, считаем это диаметром
            diameter = int(size)
            row["Размер"] = f"d{diameter}"  # модифицируем размер для обработки КР
            return process_zaglushka_kr(row)
        except ValueError:
            raise ValueError(f"Неизвестный формат размера заглушки: {size}")


# Оригинальные функции обработки (немного модифицированы для единообразия)
def process_zaglushka_pr(row):
    """ Обработка заглушки ПР """
    size = str(row["Размер"]).lower().replace("х", "x").replace("*", "x").replace(" ", "")
    width, height = map(int, size.split("x"))
    width, height = sorted([width, height], reverse=True)

    thickness = row["Толщина"]
    if pd.isna(thickness) or thickness in ["", "None", None]:
        thickness = get_thickness(width, height)
    else:
        thickness = str(thickness).replace(',', '.')
    thickness = thickness.replace('.', ',')

    quantity = int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1

    # ✅ Здесь фикс соединения
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    name = f"Заглушка ПР {width}*{height} Оц.С/{thickness}/ {connection}"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": "шт"
    }

def process_zaglushka_kr(row):
    """ Обработка Заглушек КР """
    size = str(row["Размер"]).lower().replace("d", "").strip()
    kr_diameter = int(size)

    thickness = row["Толщина"]
    if pd.isna(thickness) or thickness in ["", "None", None]:
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')
    thickness = thickness.replace('.', ',')

    quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1
    unit = "шт" if pd.isna(row["Ед. изм."]) or str(row["Ед. изм."]).strip() == "" else str(row["Ед. изм."]).strip()

    name = f"Заглушка КР d {kr_diameter} Оц.С/{thickness}/"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": unit
    }

def process_drossel(row):
    """Автоматически определяет тип дросселя (КР или ПР) и обрабатывает его"""
    size = str(row["Размер"]).strip().lower()
    
    # Проверяем, является ли размер круглым (одно число) или прямоугольным (AxB)
    if 'x' in size or '*' in size or 'х' in size:
        # Обработка Дросселя ПР
        return process_drossel_pr(row)
    else:
        # Обработка Дросселя КР
        return process_drossel_kr(row)

def process_drossel_pr(row):
    """Обработка прямоугольного дросселя"""
    size = str(row["Размер"]).lower().replace("х", "x").replace("*", "x").replace(" ", "")
    width, height = map(int, size.split("x"))

    # Толщина
    thickness = row["Толщина"]
    if pd.isna(thickness) or thickness in ["", "None", "nan"]:
        thickness = get_thickness(width, height)
    else:
        thickness = str(thickness).replace(",", ".")
    thickness = thickness.replace(".", ",")

    # Кол-во
    quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1

    # Соединение
    connection = "[30]" if width >= 1000 or height >= 1000 else "[20]"

    # Имя
    name = f"Дроссель ПР {width}*{height} Оц.С/{thickness}/ {connection}"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": "шт"
    }

def process_drossel_kr(row):
    """Обработка круглого дросселя"""
    # Извлекаем диаметр (d 100, d 125, d 160, d 250, d 315)
    size = str(row["Размер"]).replace('d', '').replace('Ø', '').replace('ф', '').strip()
    kr_diameter = int(size)

    # Определяем производителя
    manufacturer = "ГАЛВЕНТ" if kr_diameter <= 160 else "ВИНТЭЛ"

    # Если толщина не указана, подбираем по таблице
    thickness = row["Толщина"]
    if pd.isna(thickness) or thickness in ["", "None", None]:
        thickness = get_thickness(kr_diameter, kr_diameter)
    else:
        thickness = str(thickness).replace(',', '.')

    # Кол-во
    quantity = int(float(row["Кол-во"])) if not pd.isna(row["Кол-во"]) else 1

    # Ед. изм.
    unit = row["Ед. изм."]
    if pd.isna(unit) or str(unit).strip() == "":
        unit = "шт"

    # Формируем итоговое наименование
    name = f"Дроссель-клапан КР d {kr_diameter} Оц.С/{thickness.replace('.', ',')}/ [нп] {manufacturer}"

    return {
        "Наименование": name,
        "Кол-во": quantity,
        "Ед. изм.": unit
    }








import re
import math
import pandas as pd

def process_universal_pipe(row):
    """Определяет тип трубы и обрабатывает её."""
    size = str(row["Размер"]).strip().lower().replace('x', '*').replace('х', '*')
    
    if '*' not in size and '/' not in size:
        return process_spiralka_kr(row, size)
    return process_vozduh_pr(row, size)

def process_spiralka_kr(row, size):
    """Обрабатывает Спиральку КР."""
    diameter = re.sub(r'\D', '', size)
    if not diameter:
        raise ValueError("Не удалось определить диаметр спиральки")
    
    if pd.isna(row["Толщина"]):
        thickness = get_thickness(int(diameter), int(diameter))
    else:
        thickness = row["Толщина"]
    thickness = normalize_thickness(thickness)

    quantity = process_quantity(row, 3000)
    
    return {
        "Наименование": f"Спиралка КР d {diameter} -3000 Оц.С/{thickness}/ [нп]",
        "Кол-во": quantity,
        "Ед. изм.": "шт"
    }

def process_vozduh_pr(row, size):
    """Обрабатывает Воздуховод ПР."""
    size_clean = size.lower().replace('х', '*').replace('x', '*').replace(' ', '')
    width, height = map(int, sorted(map(int, size_clean.split('*')), reverse=True))
    
    if pd.isna(row["Толщина"]):
        thickness = get_thickness(width, height)
    else:
        thickness = row["Толщина"]
    thickness = normalize_thickness(thickness)

    quantity = process_quantity(row, 1250)
    connection = "[30]" if max(width, height) >= 1000 else "[20]"
    
    return {
        "Наименование": f"Воздуховод ПР {width}*{height} -1250 Оц.С/{thickness}/ {connection}",
        "Кол-во": quantity,
        "Ед. изм.": "шт"
    }

def process_quantity(row, length):
    """Обрабатывает количество, учитывая пересчёт метров в штуки."""
    quantity = 1
    if not pd.isna(row["Кол-во"]):
        try:
            quantity = float(str(row["Кол-во"]).replace(',', '.'))
            if str(row["Ед. изм."].lower()) in ['м', 'пм']:
                quantity = math.ceil((quantity * 1000) / length)
        except:
            quantity = 1
    return int(quantity)

def process_otvod(row):
    """Универсальный обработчик отводов с корректным выбором производителя ГАЛВЕНТ/ВИНТЭЛ"""
    try:
        size = str(row["Размер"]).strip().lower()
        
        # Прямоугольный отвод
        if any(sym in size for sym in ['x', 'х', '*']):
            size_clean = size.replace('*', 'x').replace('х', 'x')
            width, height = map(int, size_clean.split('x'))

            if pd.isna(row["Толщина"]) or str(row["Толщина"]).strip().lower() in ["", "none", "nan"]:
                thickness = get_thickness(width, height)
            else:
                thickness = str(row["Толщина"]).replace(',', '.')
            thickness = thickness.replace('.', ',')

            connection = "[30]" if max(width, height) >= 1000 else "[20]"
            count = 1 if row['Кол-во']=='-' else int(float(str(row["Кол-во"]).replace(',', '.')))
            return {
                "Наименование": f"Отвод ПР {width}*{height}-90° шейка 50*50 Оц.С/{thickness}/ {connection}",
                # "Кол-во": int(float(str(row["Кол-во"]).replace(',', '.'))) if not pd.isna(row["Кол-во"]) else 1,
                "Кол-во": count,
                "Ед. изм.": "шт"
            }

        # Круглый отвод
        else:
            kr_diameter = int(size.replace('d', '').replace('ф', '').replace('ø', '').strip())

            raw_angle = float(row["Угол"]) if not pd.isna(row["Угол"]) else 90
            if 0 <= raw_angle <= 44:
                angle = 45
            elif 45 <= raw_angle <= 90:
                angle = 90
            else:
                raise ValueError(f"⛔ Недопустимый угол круглого отвода: {raw_angle}° — допустимы значения 0–90°")

            # Производитель и толщина по правилам
            if kr_diameter <= 125:
                manufacturer = "ГАЛВЕНТ"
                thickness = get_thickness(kr_diameter, kr_diameter) if pd.isna(row["Толщина"]) else row["Толщина"]
            elif kr_diameter == 160:
                if angle == 90:
                    manufacturer = "ГАЛВЕНТ"
                    thickness = "0.9"
                else:  # 45°
                    manufacturer = "ВИНТЭЛ"
                    thickness = get_thickness(kr_diameter, kr_diameter) if pd.isna(row["Толщина"]) else row["Толщина"]
            else:
                manufacturer = "ВИНТЭЛ"
                thickness = get_thickness(kr_diameter, kr_diameter) if pd.isna(row["Толщина"]) else row["Толщина"]

            thickness = str(thickness).replace(',', '.').replace('.', ',')
            count = 1 if row['Кол-во']=='-' else int(float(str(row["Кол-во"]).replace(',', '.')))
            return {
                "Наименование": f"Отвод КР d {kr_diameter}-{angle}° R-150 Оц.С/{thickness}/ [нп] {manufacturer}",
                "Кол-во": count,
                "Ед. изм.": "шт"
            }

    except Exception as e:
        print(f"Ошибка обработки отвода: {e}. Строка: {traceback.format_exc()}")
        
        return {
            "Наименование": f"❌ Ошибка при обработке отвода: {e}. Строка: {row}",
            "Кол-во": 1,
            "Ед. изм.": "-"
        }



# Обновленный словарь handlers
handlers = {

    "труба": process_universal_pipe,
    "дроссель": process_drossel,
    "заглушка": process_zaglushka,
    "отвод": process_otvod, 
    "ниппель": process_nippel, 
    "дефлектор": process_deflector,
    "шумоглушитель": process_shumoglushitel,
    "регулирующий клапан": process_regulyator_klapan,
    "пенофол": process_penofol,
    "мбор": process_mbor,
    "озкс": process_ozks,
    "скотч": process_skotch,
    "тройник": process_troynik,
    "врезка": process_vrezka,
    "переход": process_perehod,
    "диффузор": process_diffuzor
}





# ------------------- Основная логика -------------------
def process_row(row):
    from pprint import pprint
    """Обработка строки с учетом регистронезависимого определения типа"""
    item_type = str(row["Наименование"]).strip().lower()  # Переводим в нижний регистр
    print(row)
    pprint(item_type)
    if item_type in handlers:
        try:
            return handlers[item_type](row)
        except Exception as e:

            print(f"❌ Ошибка при обработке {item_type}: {e}, {traceback.format_exc()}")
            return {
                "Наименование": f"❌ Ошибка при обработке {item_type}: {e}, {traceback.format_exc()}",
                "Кол-во": 1,
                "Ед. изм.": "-"
            }
    else:
        print(f"❌ Неизвестный тип: {item_type}")
        return {
            "Наименование": f"❌ Неизвестный тип: {item_type}",
            "Кол-во": 1,
            "Ед. изм.": "-"
        }


def process_row_from_list(result)->list[dict]:
    from pprint import pprint
    # ------------------- Загрузка и обработка -------------------
    # df_input = pd.read_excel("ЗАЯВКА.xlsx")
    pprint(result)
    res2=result.copy()
    list_of_dicts=[]
    for i in res2:
        # list_of_dicts.append(list(i.values()))
        #Почему-то иногда приходит не в том порядке который нужнен и нименование сдвигается
        values=[i['Длина'], i['Ед. изм.'], i['Кол-во'], i['Наименование'], i['Размер'], i['Тип'], i['Толщина'], i['Угол']]
        list_of_dicts.append(values)
    print(list_of_dicts)
    colums=["Длина", "Ед. изм.", "Кол-во", "Наименование", "Размер", "Тип", "Толщина", "Угол"]
    df_input = pd.DataFrame(np.array(list_of_dicts), columns=colums)
    # df_input.columns = ["Наименование", "Размер", "Толщина", "Кол-во", "Ед. изм.", "Угол", "Тип", "Длина"]
    # df_input.columns = ["Длина", "Ед. изм.", "Кол-во", "Наименование", "Размер", "Тип", "Толщина", "Угол"]

    processed_rows = []
    for _, row in df_input.iterrows():
        result = process_row(row)
        if result is not None:
            if isinstance(result, list):
                processed_rows.extend(result)
            else:
                processed_rows.append(result)
    df_output = pd.DataFrame(processed_rows)

    # from openpyxl.utils import get_column_letter


    # возвращаем в формате dict с полями 'Наименование', 'Ед.изм.', 'Количество'
    # pprint(df_output)
    return df_output.to_dict(orient="records")
    



    # # Сохраняем результат с автошириной колонок
    # with pd.ExcelWriter("РЕЗУЛЬТАТ.xlsx", engine="openpyxl") as writer:
    #     df_output.to_excel(writer, index=False)
        
    #     # Получаем ссылку на Excel-лист
    #     worksheet = writer.sheets["Sheet1"]

    #     # Автоширина по содержимому
    #     for i, column in enumerate(df_output.columns, 1):
    #         max_length = max(
    #             df_output[column].astype(str).map(len).max(),
    #             len(column)
    #         )
    #         worksheet.column_dimensions[get_column_letter(i)].width = max_length + 2
    # print("✅ Обработка завершена.")

    # import os
    # os.startfile("РЕЗУЛЬТАТ.xlsx")
# Вентилятор канальный круглого сечения D125, расход 75 м³/4, напор 100Та 1 шт Пластиковый 
# диффузор вытяжной Ø125 2 шт 
# Воздуховод из тонколистовой оцинкованной стали 100х150, b=0,8 55 M 
# Воздуховод круглого сечения из тонколистовой оцинкованной стали Ø125, b=0,8 15 M 
# Отвод круглого воздуховода 90° Ø125, b=0,8 5 шт 
# Отвод прямоугольного воздуховода 90° 100×150, b=0,8 1 шт 
# Отвод прямоугольного воздуховода 90° 150×100, b=0,8 1 шт
if __name__ == "__main__":  
    result = [{'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Вентилятор',
  'Размер': '125',
  'Тип': 'канальный круглого сечения',
  'Толщина': '-',
  'Угол': '-'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Диффузор',
  'Размер': '125',
  'Тип': 'вытяжной',
  'Толщина': '-',
  'Угол': '-'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Труба',
  'Размер': '100x150',
  'Тип': '-',
  'Толщина': '0,8',
  'Угол': '-'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Труба',
  'Размер': '125',
  'Тип': '-',
  'Толщина': '0,8',
  'Угол': '-'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Отвод',
  'Размер': '125',
  'Тип': '-',
  'Толщина': '0,8',
  'Угол': '90'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Отвод',
  'Размер': '100x150',
  'Тип': '-',
  'Толщина': '0,8',
  'Угол': '90'},
 {'Длина': '-',
  'Ед. изм.': '-',
  'Кол-во': '-',
  'Наименование': 'Отвод',
  'Размер': '150x100',
  'Тип': '-',
  'Толщина': '0,8',
  'Угол': '90'}]
    print(process_row_from_list(result))

