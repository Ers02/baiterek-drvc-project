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
