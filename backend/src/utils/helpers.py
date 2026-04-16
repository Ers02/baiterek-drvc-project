from datetime import date, timedelta
from ..models.plan import NeedType

def get_need_type_by_typename(type_name: str | None) -> NeedType:
    """
    Определяет тип потребности (NeedType) на основе строкового типа из ЕНС ТРУ.
    """
    if not type_name:
        return NeedType.GOODS
        
    type_name_upper = type_name.upper().strip()
    
    need_type_map = {
        'GOOD': NeedType.GOODS,
        'GOODS': NeedType.GOODS,
        'WORK': NeedType.WORKS,
        'WORKS': NeedType.WORKS,
        'SERVICE': NeedType.SERVICES,
        'SERVICES': NeedType.SERVICES
    }
    return need_type_map.get(type_name_upper, NeedType.GOODS)

def is_smr(expense_item_id: int | None) -> bool:
    """
    Проверяет, является ли статья затрат СМР.
    ID СМР = 1.
    """
    return expense_item_id == 1

def get_kz_holidays(year: int):
    """Возвращает список праздничных дней РК на указанный год."""
    holidays = [
        date(year, 1, 1),   # Новый год
        date(year, 1, 2),   # Новый год
        date(year, 1, 7),   # Рождество
        date(year, 3, 8),   # 8 марта
        date(year, 3, 21),  # Наурыз
        date(year, 3, 22),  # Наурыз
        date(year, 3, 23),  # Наурыз
        date(year, 5, 1),   # 1 мая
        date(year, 5, 7),   # День защитника Отечества
        date(year, 5, 9),   # День Победы
        date(year, 7, 6),   # День Столицы
        date(year, 8, 30),  # День Конституции (исправлено с 15 марта на 30 августа)
        date(year, 10, 25), # День Республики
        date(year, 12, 16), # День Независимости
    ]
    return holidays

def calculate_working_days(start_date, end_date):
    """Считает количество рабочих дней между датами с учетом праздников РК."""
    if not start_date or not end_date:
        return 0

    # Приводим к date если пришел datetime
    if hasattr(start_date, 'date'): start_date = start_date.date()
    if hasattr(end_date, 'date'): end_date = end_date.date()

    if start_date > end_date:
        return 0

    working_days = 0
    current_date = start_date

    # Кэшируем праздники для годов, которые пересекаем
    holidays_cache = {}

    while current_date <= end_date:
        year = current_date.year
        if year not in holidays_cache:
            holidays_cache[year] = get_kz_holidays(year)

        # 5 - суббота, 6 - воскресенье
        is_weekend = current_date.weekday() >= 5
        is_holiday = current_date in holidays_cache[year]

        if not is_weekend and not is_holiday:
            working_days += 1

        current_date += timedelta(days=1)

    return working_days
