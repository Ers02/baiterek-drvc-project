from decimal import Decimal
from src.models import models
from src.services.plan_service import _recalculate_version_metrics

def test_recalculate_metrics(db, test_user):
    # 1. Создаем план и версию
    plan = models.ProcurementPlan(plan_name="Test Plan", year=2024, created_by=test_user.id)
    db.add(plan)
    db.commit()
    
    version = models.ProcurementPlanVersion(
        plan_id=plan.id, version_number=1, status=models.PlanStatus.DRAFT, is_active=True, created_by=test_user.id
    )
    db.add(version)
    db.commit()

    # 2. Создаем справочники (минимально необходимые)
    enstru = models.Enstru(code="12345.100.000001", type_name="GOODS")
    db.add(enstru)
    
    # Товар в реестре с 50% ВЦ
    reestr = models.Reestr_KTP(enstru_code="12345.100.000001", bin_iin="111", company_name="Test", product_name="P", dvc_percent=50.0)
    db.add(reestr)
    
    cost = models.Cost_Item(id=10, name_ru="Test Cost", name_kz="Test Cost")
    source = models.Source_Funding(id=10, name_ru="Test Source", name_kz="Test Source")
    db.add_all([cost, source])
    db.commit()

    # 3. Добавляем позиции
    
    # Позиция 1: Товар, есть в реестре (50%), сумма 1000
    item1 = models.PlanItemVersion(
        version_id=version.id, item_number=1, need_type=models.NeedType.GOODS,
        trucode="12345.100.000001", expense_item_id=10, funding_source_id=10,
        quantity=10, price_per_unit=100, total_amount=1000,
        resident_share=0 # Для товаров игнорируется
    )
    
    # Позиция 2: Услуга, доля 80%, сумма 2000
    item2 = models.PlanItemVersion(
        version_id=version.id, item_number=2, need_type=models.NeedType.SERVICES,
        trucode="99999.100.000001", expense_item_id=10, funding_source_id=10,
        quantity=1, price_per_unit=2000, total_amount=2000,
        resident_share=80
    )
    
    db.add_all([item1, item2])
    db.commit()

    # 4. Запускаем пересчет
    _recalculate_version_metrics(db, version.id)
    
    # 5. Проверяем результаты
    db.refresh(version)
    db.refresh(item1)
    db.refresh(item2)
    
    # Item 1: 1000 * 50% = 500
    assert item1.min_dvc_percent == 50.0
    assert item1.vc_amount == 500.0
    
    # Item 2: 2000 * 80% = 1600
    assert item2.min_dvc_percent == 80.0
    assert item2.vc_amount == 1600.0
    
    # Version Total: 1000 + 2000 = 3000
    assert version.total_amount == 3000.0
    
    # Version VC: 500 + 1600 = 2100
    assert version.vc_amount == 2100.0
    
    # Version VC %: 2100 / 3000 = 70%
    assert version.vc_percentage == 70.0
