from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Numeric, Index, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base

class ExternalDocument(Base):
    __tablename__ = "external_documents"
    id = Column(Integer, primary_key=True)
    doc_type = Column(String(20), nullable=False)
    bank_name = Column(String(255), nullable=False)
    
    # Данные отправителя из дочерней организации
    sender_first_name = Column(String(100), nullable=True)
    sender_last_name = Column(String(100), nullable=True)
    sender_patronymic = Column(String(100), nullable=True)
    sender_email = Column(String(255), nullable=True)
    sender_phone = Column(String(50), nullable=True)
    
    # Данные для интеграции
    external_id = Column(String(100), nullable=True, index=True)  # ID документа во внешней системе
    callback_url = Column(String(500), nullable=True)            # URL для отправки результата

    received_at = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String(500), nullable=False)

    # NEW -> PARSING -> ASSIGNED_TO_ANALYST -> ANALYST_WORKING -> FOR_APPROVAL -> APPROVED -> COMPLETED
    # REJECTED_BY_DIRECTOR (возвращено аналитику)
    status = Column(String(50), default="NEW")

    result_file_path = Column(String(500), nullable=True) # Путь к ZIP архиву (отчет + заключение)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    analyst_comment = Column(Text, nullable=True) # Комментарий аналитика для заключения
    director_comment = Column(Text, nullable=True) # Комментарий директора при возврате на доработку

    deadline_days = Column(Integer, nullable=True) # Срок в рабочих днях
    deadline_at = Column(DateTime(timezone=True), nullable=True) # Рассчитанная дата дедлайна

    completed_at = Column(DateTime(timezone=True), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Новое поле для тестовых проектов
    is_test = Column(Boolean, default=False, server_default='false')

    assigned_user = relationship("User", foreign_keys=[assigned_to])

class PsdDocumentItem(Base):
    __tablename__ = "psd_document_items"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("external_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    position_number = Column(String(50), nullable=True)
    name = Column(Text, nullable=False)
    code_sn = Column(String(50), nullable=True)
    unit = Column(String(100), nullable=True)
    volume = Column(Numeric(15, 3), default=0)
    price = Column(Numeric(18, 2), default=0)
    total_amount = Column(Numeric(18, 2), default=0)
    category = Column(String(50), nullable=True)
    clean_name = Column(Text, nullable=True)
    is_product = Column(Boolean, default=True)
    skip_search = Column(Boolean, default=False)
    not_in_ktp_registry = Column(Boolean, default=False)
    # Убрали ForeignKey на enstru - код ENSTRU берем из Реестра КТП, не из справочника
    enstru_code = Column(String(35), nullable=True)
    enstru_name = Column(Text, nullable=True)
    match_type = Column(String(20), default="none")
    match_score = Column(Integer, nullable=True)
    match_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    item_type = Column(String(100), nullable=True, server_default='GOODS')
    __table_args__ = (
        Index('idx_psd_items_doc_id', 'document_id'),
        Index('idx_psd_items_code_sn', 'code_sn'),
    )


class AgskEnstruMatch(Base):
    """Ручные сопоставления аналитиков АГСК → ЕНСТРУ, требующие утверждения менеджера"""
    __tablename__ = "agsk_enstru_matches"
    id = Column(Integer, primary_key=True)
    agsk_code = Column(String(50), nullable=False)
    enstru_code = Column(String(35), nullable=False)
    # Контекст: если doc_id/item_id заполнены — сопоставление в рамках документа ПСД
    # Если null — общее глобальное сопоставление АГСК→ЕНСТРУ
    doc_id = Column(Integer, ForeignKey("external_documents.id", ondelete="CASCADE"), nullable=True)
    item_id = Column(Integer, ForeignKey("psd_document_items.id", ondelete="CASCADE"), nullable=True)
    matched_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
    is_approved = Column(Boolean, default=False, nullable=False, server_default='false')
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default='true')

    __table_args__ = (
        Index('idx_aem_agsk_code', 'agsk_code'),
        Index('idx_aem_item_id', 'item_id'),
        Index('idx_aem_doc_id', 'doc_id'),
        Index('idx_aem_matched_by', 'matched_by'),
    )


class PsdAnalysisSession(Base):
    __tablename__ = "psd_analysis_sessions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("external_documents.id", ondelete="CASCADE"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), default="in_progress")
    total_agsk_count = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    manual_match_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result_file_path = Column(String(500), nullable=True)

class AdminTask(Base):
    __tablename__ = "admin_tasks"
    id = Column(String(36), primary_key=True)
    status = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    result_file = Column(String(255), nullable=True)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
