from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Enum, DateTime
from sqlalchemy.sql import func
from src.database.base import Base
import enum


class ApplicationState(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PRE_APPROVED = "pre_approved"
    BANK_DISCUSSED = "bank_discussed"      # после похода в банк
    FINAL_APPROVED = "final_approved"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)  # № заявки

    # Основные поля
    need_type = Column(String, nullable=False)  # Вид потребности
    enstru_code = Column(String)  # Код по ЕНС ТРУ
    enstru_name = Column(Text)    # Наименование по коду
    enstru_specs = Column(Text)   # Характеристики по коду
    additional_specs = Column(Text)  # Дополнительная характеристика (свободно)

    agsk_3 = Column(String)  # АГСК-3 (для СМР)
    expense_item = Column(String)  # Статья затрат
    funding_source = Column(String)  # Источник финансирования

    kato_purchase = Column(String)   # Код КАТО места закупки
    kato_delivery = Column(String)   # Код КАТО места поставки

    unit = Column(String)            # Единица измерения (МКЕИ)
    quantity = Column(Float)
    marketing_price = Column(Float)  # Цена без НДС
    marketing_total = Column(Float)  # Сумма маркетинговая
    planned_total_no_vat = Column(Float)  # Планируемая сумма без НДС

    is_ktp = Column(Boolean, default=False)  # Признак КТП / Резидент РК
    ktp_applicable = Column(Boolean, default=False)  # Применима ли закупка у КТП

    state = Column(Enum(ApplicationState), default=ApplicationState.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())