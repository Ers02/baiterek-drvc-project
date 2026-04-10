import enum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, SmallInteger, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base

class PlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PRE_APPROVED = "PRE_APPROVED"
    APPROVED = "APPROVED"

class NeedType(enum.Enum):
    GOODS = "Товар"
    WORKS = "Работа"
    SERVICES = "Услуга"

class ProcurementPlan(Base):
    __tablename__ = "procurement_plans"

    id = Column(Integer, primary_key=True)
    plan_name = Column(String(500), nullable=False)
    year = Column(SmallInteger, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="plans")
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
    import_percentage = Column(Numeric(5, 2))
    
    vc_percentage = Column(Numeric(5, 2), default=0)
    vc_amount = Column(Numeric(20, 2), default=0)
    
    executed_vc_amount = Column(Numeric(20, 2), default=0)
    executed_vc_percentage = Column(Numeric(5, 2), default=0)

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

    additional_specs = Column(Text, nullable=True)
    additional_specs_kz = Column(Text, nullable=True)

    quantity = Column(Numeric(12, 3), nullable=False)
    price_per_unit = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)

    is_ktp = Column(Boolean, default=False)

    # Новые поля для резидентства
    resident_share = Column(Numeric(5, 2), default=100, nullable=False)
    non_resident_reason = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False)

    root_item_id = Column(Integer, ForeignKey("plan_item_versions.id"), index=True, nullable=True)
    source_version_id = Column(Integer, ForeignKey("procurement_plan_versions.id"), nullable=True)

    revision_number = Column(Integer, default=0, nullable=False)

    executed_quantity = Column(Numeric(12, 3), default=0, nullable=False)
    executed_amount = Column(Numeric(18, 2), default=0, nullable=False)

    min_dvc_percent = Column(Numeric(5, 2), default=0)
    vc_amount = Column(Numeric(18, 2), default=0)  # Новое поле: сумма ВЦ по позиции

    # Новое поле: исполненная сумма ВЦ
    executed_vc_amount = Column(Numeric(18, 2), default=0)

    # Новое поле: оригинальное название единицы измерения (для импорта)
    original_unit_name = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    version = relationship("ProcurementPlanVersion", back_populates="items", foreign_keys=[version_id])
    source_version = relationship("ProcurementPlanVersion", foreign_keys=[source_version_id])

    root_item = relationship("PlanItemVersion", remote_side=[id], foreign_keys=[root_item_id], post_update=True)

    enstru = relationship("Enstru")
    unit = relationship("Mkei")
    expense_item = relationship("Cost_Item")
    funding_source = relationship("Source_Funding")
    agsk = relationship("Agsk")
    kato_purchase = relationship("Kato", foreign_keys=[kato_purchase_id])
    kato_delivery = relationship("Kato", foreign_keys=[kato_delivery_id])

    executions = relationship("PlanItemExecution", back_populates="plan_item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("version_id", "item_number", "need_type", name="uq_version_item_type"),
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
    
    contract_number = Column(String(100), nullable=False)
    contract_date = Column(Date, nullable=False)
    
    contract_quantity = Column(Numeric(12, 3), nullable=False)
    contract_price_per_unit = Column(Numeric(18, 2), nullable=False)
    contract_sum = Column(Numeric(18, 2), nullable=False)
    
    fact_vc_percentage = Column(Numeric(5, 2), default=0)
    fact_vc_amount = Column(Numeric(18, 2), default=0)
    
    supply_volume_physical = Column(Numeric(12, 3), nullable=False)
    supply_volume_value = Column(Numeric(18, 2), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    plan_item = relationship("PlanItemVersion", back_populates="executions")
