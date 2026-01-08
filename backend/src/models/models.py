from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, SmallInteger, UniqueConstraint, Enum, and_, Float, text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base
import enum


class PlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PRE_APPROVED = "PRE_APPROVED"
    APPROVED = "APPROVED"


class NeedType(enum.Enum):
    GOODS = "Товар"
    WORKS = "Работа"
    SERVICES = "Услуга"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    iin = Column(String(12), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    bin = Column(String(12), index=True)
    org_name = Column(String(500))
    email = Column(String(255))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    plans = relationship("ProcurementPlan", back_populates="creator")

class ProcurementPlan(Base):
    __tablename__ = "procurement_plans"

    id = Column(Integer, primary_key=True)
    plan_name = Column(String(500), nullable=False)
    year = Column(SmallInteger, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
    versions = relationship(
        "ProcurementPlanVersion",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ProcurementPlanVersion.version_number"
    )

class ProcurementPlanVersion(Base):
    __tablename__ = "procurement_plan_versions"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("procurement_plans.id", ondelete="CASCADE"))
    version_number = Column(Integer, nullable=False)

    status = Column(Enum(PlanStatus), nullable=False)

    total_amount = Column(Numeric(20, 2), default=0)
    ktp_percentage = Column(Numeric(5, 2))
    import_percentage = Column(Numeric(5, 2))
    
    # Новые поля для статистики ВЦ (Value Creation)
    vc_mean = Column(Numeric(5, 2), default=0) # Среднее значение
    vc_median = Column(Numeric(5, 2), default=0) # Медиана
    vc_amount = Column(Numeric(20, 2), default=0) # Количественное (сумма)

    is_active = Column(Boolean, default=True)
    is_executed = Column(Boolean, default=False, nullable=False)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("ProcurementPlan", back_populates="versions")
    
    items = relationship(
        "PlanItemVersion",
        back_populates="version",
        cascade="all, delete-orphan",
        foreign_keys="[PlanItemVersion.version_id]"
    )

    __table_args__ = (
        UniqueConstraint("plan_id", "version_number", name="uq_plan_version"),
    )
    creator = relationship("User")

class PlanItemVersion(Base):
    __tablename__ = "plan_item_versions"

    id = Column(Integer, primary_key=True)
    version_id = Column(
        Integer,
        ForeignKey("procurement_plan_versions.id", ondelete="CASCADE"),
        nullable=False
    )

    item_number = Column(Integer, nullable=False)
    need_type = Column(Enum(NeedType), nullable=False)

    trucode = Column(String(35), ForeignKey("enstru.code"), nullable=False)
    unit_id = Column(Integer, ForeignKey("mkei.id"))
    expense_item_id = Column(Integer, ForeignKey("cost_items.id"), nullable=False)
    funding_source_id = Column(Integer, ForeignKey("source_funding.id"), nullable=False)

    agsk_id = Column(String(50), ForeignKey("agsk.code"))
    kato_purchase_id = Column(Integer, ForeignKey("kato.id"))
    kato_delivery_id = Column(Integer, ForeignKey("kato.id"))

    quantity = Column(Numeric(12, 3), nullable=False)
    price_per_unit = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)

    is_ktp = Column(Boolean, default=False)
    is_resident = Column(Boolean, default=False)
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    root_item_id = Column(Integer, ForeignKey("plan_item_versions.id"), index=True, nullable=True)
    source_version_id = Column(Integer, ForeignKey("procurement_plan_versions.id"), nullable=True)
    
    # Новое поле: номер редакции (0 - оригинал, 1 - первая правка и т.д.)
    revision_number = Column(Integer, default=0, nullable=False,server_default=text('0'))
    
    executed_quantity = Column(Numeric(12, 3), default=0, nullable=False)
    executed_amount = Column(Numeric(18, 2), default=0, nullable=False)
    
    min_dvc_percent = Column(Numeric(5, 2), default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    version = relationship("ProcurementPlanVersion", back_populates="items", foreign_keys=[version_id])
    source_version = relationship("ProcurementPlanVersion", foreign_keys=[source_version_id])
    
    root_item = relationship("PlanItemVersion", remote_side=[id], foreign_keys=[root_item_id])
    
    enstru = relationship("Enstru")
    unit = relationship("Mkei")
    expense_item = relationship("Cost_Item")
    funding_source = relationship("Source_Funding")
    agsk = relationship("Agsk")
    kato_purchase = relationship("Kato", foreign_keys=[kato_purchase_id])
    kato_delivery = relationship("Kato", foreign_keys=[kato_delivery_id])
    
    executions = relationship("PlanItemExecution", back_populates="plan_item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("version_id", "item_number", name="uq_version_item"),
    )
    
    @property
    def start_version_number(self):
        """Возвращает номер версии, в которой была создана эта позиция."""
        if self.root_item and self.root_item.version:
            return self.root_item.version.version_number
        if self.version:
             return self.version.version_number
        return 1

class PlanItemExecution(Base):
    __tablename__ = "plan_item_executions"

    id = Column(Integer, primary_key=True)
    plan_item_id = Column(Integer, ForeignKey("plan_item_versions.id", ondelete="CASCADE"), nullable=False)
    
    supplier_name = Column(String(500), nullable=False)
    supplier_bin = Column(String(12), nullable=False)
    residency_code = Column(String(50), nullable=False)
    origin_code = Column(String(50), nullable=False)
    
    contract_number = Column(String(100), nullable=False)
    contract_date = Column(Date, nullable=False)
    
    contract_quantity = Column(Numeric(12, 3), nullable=False)
    contract_price_per_unit = Column(Numeric(18, 2), nullable=False)
    contract_sum = Column(Numeric(18, 2), nullable=False)
    
    supply_volume_physical = Column(Numeric(12, 3), nullable=False)
    supply_volume_value = Column(Numeric(18, 2), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    plan_item = relationship("PlanItemVersion", back_populates="executions")


class Mkei(Base):
    __tablename__ = "mkei"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name_kz = Column(Text, nullable=False)
    name_ru = Column(Text, nullable=False)

class Kato(Base):
    __tablename__ = "kato"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer)
    code = Column(String(20), unique=True, nullable=False)
    name_kz = Column(Text, nullable=False)
    name_ru = Column(Text, nullable=False)

class Agsk(Base):
    __tablename__ = "agsk"
    id = Column(Integer, primary_key=True)
    group = Column(Text, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    name_ru = Column(Text, nullable=False)
    standart = Column(Text, nullable=True)
    unit = Column(Text, nullable=True)

class Cost_Item(Base):
    __tablename__ = "cost_items"
    id = Column(Integer, primary_key=True)
    name_ru = Column(Text, nullable=False)
    name_kz = Column(Text, nullable=False)

class Source_Funding(Base):
    __tablename__ = "source_funding"
    id = Column(Integer, primary_key=True)
    name_ru = Column(Text, nullable=False)
    name_kz = Column(Text, nullable=False)

class Enstru(Base):
    __tablename__ = "enstru"
    id = Column(Integer, primary_key=True)
    code = Column(String(35), unique=True, nullable=False)
    name_ru = Column(Text, nullable=False)
    name_kz = Column(Text, nullable=False)
    type_ru = Column(Text, nullable=False)
    type_kz = Column(Text, nullable=False)
    specs_ru = Column(Text, nullable=True)
    specs_kz = Column(Text, nullable=True)

class Reestr_KTP(Base):
    __tablename__ = "reestr_ktp"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), nullable=True)          # Код товара (иногда содержит буквы)
    registration_number = Column(String(50), nullable=True)   # Рег. номер (может быть длинным)
    bin_iin = Column(String(12), nullable=False, index=True)  # БИН/ИИН всегда 12 символов
    company_name = Column(String(500), nullable=False)        # Название компании
    oked_codes = Column(String(50), nullable=True)            # Коды ОКЭД
    oked_names = Column(Text, nullable=True)                  # Расшифровка ОКЭД
    region_kato = Column(String(50), nullable=True)           # Код или название региона
    production_address = Column(Text, nullable=True)          # Адрес производства
    website = Column(String(255), nullable=True)              # Сайт
    phone = Column(String(100), nullable=True)                # Телефон (строка, т.к. могут быть скобки/дефисы)
    email = Column(String(255), nullable=True)                # Email
    product_name = Column(Text, nullable=False)               # Наименование товара
    production_capacity = Column(String(255), nullable=True)  # Мощность (может быть "100 тонн в год")
    tnved_code_10 = Column(String(10), nullable=True)         # ТНВЭД (обычно 10 цифр)
    kpved_code = Column(String(20), nullable=True)            # КПВЭД код
    kpved_name = Column(Text, nullable=True)                  # КПВЭД название
    enstru_code = Column(String(50), nullable=True)           # ЕНС ТРУ код
    enstru_name = Column(Text, nullable=True)                 # ЕНС ТРУ название
    agsk3_code = Column(String(50), nullable=True)            # АГСК код
    agsk3_name = Column(Text, nullable=True)                  # АГСК название
    dvc_percent = Column(Float, nullable=True)                # Доля внутристрановой ценности (%)
    localization_level = Column(Integer, nullable=True)       # Уровень локализации (число)
    registry_inclusion_date = Column(Date, nullable=True)     # Дата включения в реестр
