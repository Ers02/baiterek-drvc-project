from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Numeric, Index, UniqueConstraint, Date
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
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
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

    __table_args__ = (
        Index('idx_psd_items_doc_id', 'document_id'),
        Index('idx_psd_items_code_sn', 'code_sn'),
    )

class AgskReestrKtpMatch(Base):
    """Библиотека замен: связь AGSK с несколькими товарами из Реестра КТП"""
    __tablename__ = "agsk_reestr_ktp_matches"
    id = Column(Integer, primary_key=True)
    agsk_code = Column(String(50), nullable=False, index=True)
    # Убрали ForeignKey на enstru.code - сопоставление идет с Реестром КТП, не со справочником
    enstru_code = Column(String(35), nullable=False, index=True)
    
    ktp_id = Column(Integer, ForeignKey("reestr_ktp.id"), nullable=False)
    
    source = Column(String(20), default="manual")
    agsk_name_ru = Column(Text, nullable=True)
    enstru_name_ru = Column(Text, nullable=True)
    product_name_ktp = Column(Text, nullable=True)
    
    dvc_percent = Column(Numeric(5, 2), nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    psd_document_id = Column(Integer, ForeignKey("external_documents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        UniqueConstraint('agsk_code', 'enstru_code', 'ktp_id', name='uq_agsk_reestr_ktp_manual_v2'),
    )

class PsdAnalysisSession(Base):
    __tablename__ = "psd_analysis_sessions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("external_documents.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
