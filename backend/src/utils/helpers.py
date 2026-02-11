from ..models import models

def get_need_type_by_typename(type_name: str | None) -> models.NeedType:
    """
    Определяет тип потребности (NeedType) на основе строкового типа из ЕНС ТРУ.
    """
    if not type_name:
        return models.NeedType.GOODS
        
    type_name_upper = type_name.upper().strip()
    
    need_type_map = {
        'GOOD': models.NeedType.GOODS,
        'GOODS': models.NeedType.GOODS,
        'WORK': models.NeedType.WORKS,
        'WORKS': models.NeedType.WORKS,
        'SERVICE': models.NeedType.SERVICES,
        'SERVICES': models.NeedType.SERVICES
    }
    return need_type_map.get(type_name_upper, models.NeedType.GOODS)

def is_smr(expense_item_id: int | None) -> bool:
    """
    Проверяет, является ли статья затрат СМР (Строительно-монтажные работы).
    ID СМР = 1.
    """
    return expense_item_id == 1
