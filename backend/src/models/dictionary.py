from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from ..database.base import Base

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
    group = Column(Text, nullable=True)
    code = Column(Text, unique=True, nullable=True) # Добавлено unique=True
    name_ru = Column(Text, nullable=True)
    full_name = Column(Text, nullable=True)
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
    standard = Column(Text, nullable=True)
    detail_rus = Column(Text, nullable=True)
    type_name = Column(String(50), nullable=True)
    code = Column(String(35), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    name_rus = Column(Text, nullable=True)
    modify_datetime = Column(DateTime, nullable=True)
    name_kaz = Column(Text, nullable=True)
    type = Column(String(20), nullable=True)
    detail_eng = Column(Text, nullable=True)
    uom = Column(String(50), nullable=True)
    name_eng = Column(Text, nullable=True)
    detail_kaz = Column(Text, nullable=True)
    create_datetime = Column(DateTime, nullable=True)
    new_code = Column(String(35), nullable=True)
    purchasing_group_name = Column(Text, nullable=True)
    purchasing_subgroup_name = Column(Text, nullable=True)

class Reestr_KTP(Base):
    __tablename__ = "reestr_ktp"
    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(Text, nullable=True)
    registration_number = Column(Text, nullable=True)
    bin_iin = Column(Text, nullable=True)
    company_name = Column(Text, nullable=True)
    oked_codes = Column(JSONB, nullable=True)
    oked_names = Column(JSONB, nullable=True)
    region_kato = Column(Text, nullable=True)
    production_address = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    product_name = Column(Text, nullable=True)
    production_capacity = Column(Text, nullable=True)
    tnved_codes = Column(JSONB, nullable=True)
    kpved_codes = Column(JSONB, nullable=True)
    kpved_names = Column(JSONB, nullable=True)
    enstru_codes = Column(JSONB, nullable=True)
    enstru_names = Column(JSONB, nullable=True)
    agsk3_codes = Column(JSONB, nullable=True)
    agsk3_names = Column(JSONB, nullable=True)
    dvc_percent = Column(Text, nullable=True)
    localization_level = Column(Text, nullable=True)
    registry_inclusion_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=True)
    hidden_at = Column(DateTime, nullable=True)
    hidden_reason = Column(Text, nullable=True)
    data_source = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_reestr_ktp_agsk3_codes', "agsk3_codes", postgresql_using='gin'),
        Index('idx_reestr_ktp_enstru_codes', "enstru_codes", postgresql_using='gin'),
        Index('idx_reestr_ktp_oked_codes', "oked_codes", postgresql_using='gin'),
        Index('idx_reestr_ktp_kpved_codes', "kpved_codes", postgresql_using='gin'),
        Index('idx_reestr_ktp_tnved_codes', "tnved_codes", postgresql_using='gin'),
    )


class Oked(Base):
    __tablename__ = "oked"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=True)
    name_kz = Column(String(512), nullable=True)
    name_ru = Column(String(512), nullable=True)
    parent_identificator = Column(String(50), nullable=True)


class Kpved(Base):
    __tablename__ = "kpved"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=True)
    name_kz = Column(String(1024), nullable=True)
    name_ru = Column(String(1024), nullable=True)
    parent_identificator = Column(String(50), nullable=True)


class Tnved(Base):
    __tablename__ = "tnved"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=True)
    tree_name = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    parent_id = Column(Integer, nullable=True)
    is_last = Column(Boolean, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
