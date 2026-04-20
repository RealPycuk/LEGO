# models.py
from datetime import datetime
from sqlalchemy import JSON, DateTime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Classificator(Base):
    __tablename__ = "классификатор"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    название = Column(String(100), nullable=False)
    тип_элемента = Column(String(20), nullable=False)
    родительский_id = Column(Integer, ForeignKey("классификатор.id", ondelete="SET NULL"), nullable=True)
    порядок_сортировки = Column(Integer, default=0)
    базовая_ед_измерения = Column(Integer, nullable=True)
    
    # Relationships
    children = relationship("Classificator", backref="parent", remote_side=[id])
    theme = relationship("Theme", back_populates="classificator", uselist=False)
    age_category = relationship("AgeCategory", back_populates="classificator", uselist=False)
    part_type = relationship("PartType", back_populates="classificator", uselist=False)
    product_set = relationship("Set", back_populates="classificator", uselist=False)
    part = relationship("Part", back_populates="classificator", uselist=False)
    minifigure = relationship("Minifigure", back_populates="classificator", uselist=False)


class Theme(Base):
    __tablename__ = "тематика"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    описание = Column(Text)
    
    # Relationships
    classificator = relationship("Classificator", back_populates="theme")
    sets = relationship("Set", back_populates="theme")


class AgeCategory(Base):
    __tablename__ = "возрастная_категория"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    минимальный_возраст = Column(Integer, nullable=False)
    максимальный_возраст = Column(Integer, nullable=False)
    
    # Relationships
    classificator = relationship("Classificator", back_populates="age_category")
    sets = relationship("Set", back_populates="age_category")


class PartType(Base):
    __tablename__ = "тип_детали"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    уровень_иерархии = Column(Integer)
    
    # Relationships
    classificator = relationship("Classificator", back_populates="part_type")
    parts = relationship("Part", back_populates="part_type")


class Set(Base):
    __tablename__ = "набор"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    номер_по_каталогу = Column(String(20), nullable=False, unique=True)
    количество_деталей = Column(Integer)
    год_выпуска = Column(Integer)
    цена = Column(Float)
    id_возрастной_категории = Column(Integer, ForeignKey("возрастная_категория.id"))
    id_тематики = Column(Integer, ForeignKey("тематика.id"))
    
    # Relationships
    classificator = relationship("Classificator", back_populates="product_set")
    age_category = relationship("AgeCategory", back_populates="sets")
    theme = relationship("Theme", back_populates="sets")
    parts = relationship("SetPart", back_populates="set")
    minifigures = relationship("SetMinifigure", back_populates="set")


class Part(Base):
    __tablename__ = "деталь"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    цвет = Column(String(30))
    размер = Column(String(20))
    вес = Column(Float)
    id_типа = Column(Integer, ForeignKey("тип_детали.id"))
    
    # Relationships
    classificator = relationship("Classificator", back_populates="part")
    part_type = relationship("PartType", back_populates="parts")
    sets = relationship("SetPart", back_populates="part")


class Minifigure(Base):
    __tablename__ = "мини_фигурка"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_классификатора = Column(Integer, ForeignKey("классификатор.id", ondelete="CASCADE"), unique=True)
    персонаж = Column(String(100))
    серия = Column(String(50))
    уникальный_код = Column(String(20), unique=True)
    
    # Relationships
    classificator = relationship("Classificator", back_populates="minifigure")
    sets = relationship("SetMinifigure", back_populates="minifigure")


class SetPart(Base):
    __tablename__ = "состав_набора"
    
    id_набора = Column(Integer, ForeignKey("набор.id", ondelete="CASCADE"), primary_key=True)
    id_детали = Column(Integer, ForeignKey("деталь.id", ondelete="CASCADE"), primary_key=True)
    количество_штук = Column(Integer)
    
    # Relationships
    set = relationship("Set", back_populates="parts")
    part = relationship("Part", back_populates="sets")


class SetMinifigure(Base):
    __tablename__ = "фигурки_в_наборе"
    
    id_набора = Column(Integer, ForeignKey("набор.id", ondelete="CASCADE"), primary_key=True)
    id_фигурки = Column(Integer, ForeignKey("мини_фигурка.id", ondelete="CASCADE"), primary_key=True)
    количество_штук = Column(Integer)
    
    # Relationships
    set = relationship("Set", back_populates="minifigures")
    minifigure = relationship("Minifigure", back_populates="sets")


class Enumeration(Base):
    """Справочник перечислений (тип enum)"""
    __tablename__ = "перечисление"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    values = relationship("EnumValue", back_populates="enumeration", cascade="all, delete-orphan")

class EnumValue(Base):
    """Значение перечисления"""
    __tablename__ = "значение_перечисления"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enumeration_id = Column(Integer, ForeignKey("перечисление.id", ondelete="CASCADE"), nullable=False)
    value = Column(String(200), nullable=False)
    sort_order = Column(Integer, default=0)
    extra_data = Column(JSON, nullable=True)

    enumeration = relationship("Enumeration", back_populates="values")