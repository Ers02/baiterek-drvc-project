import re
from typing import List, Dict, Tuple

# Паттерны для определения "не-товаров" по названию (работы, услуги)
NON_PRODUCT_PATTERNS = re.compile(
    r'\b(монтаж|установка|демонтаж|укладка|прокладка|устройство|разработка|'
    r'изготовление|нанесение|окраска|сборка|разборка|испытание|наладка|'
    r'пусконаладк|бурение|сварка|заливка|утрамбовк)\b',
    re.IGNORECASE
)

HAS_LETTERS_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁ]')

STOP_WORDS = {"из", "в", "на", "по", "для", "с", "и", "или", "а", "от", "до",
                "при", "за", "не", "под", "над", "марки", "тип", "типа",
                "мм", "см", "кг", "шт", "гост"}

def clean_product_name(name: str) -> str:
    """
    Очищает название для поиска:
    убирает ГОСТы, размерные характеристики, уточнения в скобках.
    """
    if not name:
        return ""
    # Убираем ГОСТ, СТ РК, ISO, ТУ
    name = re.sub(r'(ГОСТ|СТ\s*РК|ISO|ТУ)[\s\w.\-\/]+', '', name, flags=re.IGNORECASE)
    # Убираем содержимое скобок
    name = re.sub(r'\([^)]*\)', '', name)
    # Убираем всё после /
    name = name.split('/')[0]
    # Убираем размеры
    name = re.sub(r'\b\d+[\s]*(мм|см|м|кг|т|шт|л)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+[\s]*[хxXХ][\s]*\d+\b', '', name)
    # Убираем одиночные числа
    name = re.sub(r'\b\d+\b', '', name)
    # Нормализуем пробелы
    return re.sub(r'\s+', ' ', name).strip()

def is_non_product(name: str) -> bool:
    """Определяет, является ли позиция работой/услугой, а не товаром."""
    if not name:
        return False
    return bool(NON_PRODUCT_PATTERNS.search(name))

def has_letters(text: str) -> bool:
    if not text:
        return False
    return bool(HAS_LETTERS_RE.search(text))

def tokenize(text: str) -> List[str]:
    """Токенизация текста для поиска"""
    if not text:
        return []
    words = re.findall(r"[а-яёa-z0-9][а-яёa-z0-9,./\-]*", text.lower())
    return [w for w in words if len(w) >= 2 and w not in STOP_WORDS]

def score_pair(agsk: Dict, enstru: Dict) -> Tuple[int, str]:
    """Оценка соответствия AGSK и ENSTRU (0-100)"""
    from rapidfuzz import fuzz # Импортируем здесь чтобы избежать проблем
    
    full = (agsk.get("full_name") or "").strip().lower()
    name_ru = (agsk.get("name_ru") or "").strip().lower()
    standart_a = (agsk.get("standart") or "").strip().lower()
    
    name = (enstru.get("name_rus") or "").strip().lower()
    detail = (enstru.get("detail_rus") or "").strip().lower()
    standard = (enstru.get("standard") or "").strip().lower()
    
    if not name or not full:
        return 0, "пустые поля"
    
    reasons = []
    score = 0
    
    # 1. Название enstru входит в full_name agsk (до 50 баллов)
    if name in full:
        score += 50
        reasons.append(f"'{name}' входит в full_name")
    else:
        name_tokens = tokenize(name)
        full_tokens = set(tokenize(full))
        if name_tokens:
            matched = [t for t in name_tokens if t in full_tokens]
            ratio = len(matched) / len(name_tokens)
            if ratio >= 0.8:
                score += 35
                reasons.append(f"{int(ratio*100)}% слов name в full_name")
            elif ratio >= 0.5:
                score += 15
                reasons.append(f"{int(ratio*100)}% слов name в full_name")
            else:
                fs = fuzz.token_set_ratio(name, full)
                if fs >= 60:
                    score += int(fs * 0.3)
                    reasons.append(f"fuzzy={fs}%")
    
    # 2. detail_rus (до 30 баллов)
    if detail:
        detail_tokens = tokenize(detail)
        full_tokens = set(tokenize(full))
        if detail_tokens:
            matched_d = [t for t in detail_tokens if t in full_tokens]
            ratio_d = len(matched_d) / len(detail_tokens)
            if ratio_d >= 0.6:
                score += int(30 * ratio_d)
                reasons.append(f"detail совпал на {int(ratio_d*100)}%")
            elif ratio_d >= 0.3:
                score += int(15 * ratio_d)
                reasons.append(f"detail частично {int(ratio_d*100)}%")
    
    # 3. Стандарт (до 20 баллов)
    if standard:
        std_tokens = tokenize(standard)
        combined_tokens = set(tokenize(full + " " + standart_a))
        if std_tokens:
            matched_s = [t for t in std_tokens if t in combined_tokens]
            ratio_s = len(matched_s) / len(std_tokens)
            if ratio_s >= 0.5:
                score += int(20 * ratio_s)
                reasons.append(f"стандарт совпал на {int(ratio_s*100)}%")
    
    return min(100, max(0, score)), " | ".join(reasons) or "нет совпадений"
