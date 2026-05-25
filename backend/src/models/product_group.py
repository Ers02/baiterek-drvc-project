from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database.base import Base


class ProductGroup(Base):
    """Группа/товар для аналитики - библиотека условий"""
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)  # Название группы/товара

    # Коды справочников в формате JSONB - только коды (строки)
    oked_codes = Column(JSON, nullable=True, default=list)  # ["A.01.11.1", "A.01.12.0"]
    kpved_codes = Column(JSON, nullable=True, default=list)  # ["01.11.11", "01.12.12"]
    enstru_codes = Column(JSON, nullable=True, default=list)  # ["001.001.001", "002.002.002"]
    agsk3_codes = Column(JSON, nullable=True, default=list)  # ["10001000", "10002000"]
    tnved_codes = Column(JSON, nullable=True, default=list)  # ["0101.21.001", "0202.32.002"]

    # Коды product_code из реестра КТП (JSONB) - только строки для связи
    reestr_ktp_codes = Column(JSON, nullable=True, default=list)  # ["PRD-001", "PRD-002"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Связь с пользователем
    creator = relationship("User", foreign_keys=[created_by])


class ProductGroupSet(Base):
    """Набор групп/товаров для аналитики"""
    __tablename__ = "product_group_sets"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Связь с группами
    items = relationship("ProductGroupSetItem", back_populates="set_obj", cascade="all, delete-orphan")


class ProductGroupSetItem(Base):
    """Связующая таблица для набора групп"""
    __tablename__ = "product_group_set_items"

    id = Column(Integer, primary_key=True)
    set_id = Column(Integer, ForeignKey("product_group_sets.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("product_groups.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)

    set_obj = relationship("ProductGroupSet", back_populates="items")
    group = relationship("ProductGroup")
