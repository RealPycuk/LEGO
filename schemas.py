# schemas.py
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Category schemas
class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    node_type: str
    sort_order: int = 0
    
    class Config:
        from_attributes = True

# Subcategory
class SubcategoryCreate(BaseModel):
    parent_name: str
    child_name: str

# Move node
class MoveNode(BaseModel):
    new_parent_id: Optional[int] = None

# Reorder children
class ReorderChildren(BaseModel):
    ordered_child_ids: List[int]

# Set base unit
class SetBaseUnit(BaseModel):
    base_ei_id: int

# Set schemas
class SetCreate(BaseModel):
    name: str
    catalog_number: str
    year: int
    price: float
    parts_count: int
    age_category_id: int
    theme_id: int
    parent_id: Optional[int] = None

class SetResponse(BaseModel):
    id: int
    name: str
    catalog_number: str
    year: int
    price: float
    parts_count: int
    
    class Config:
        from_attributes = True

# Part schemas
class PartCreate(BaseModel):
    name: str
    color: str
    size: str
    weight: float
    part_type_id: int

class PartResponse(BaseModel):
    id: int
    name: str
    color: str
    size: str
    weight: float
    part_type_id: int
    
    class Config:
        from_attributes = True

# Minifigure schemas
class MinifigureCreate(BaseModel):
    name: str
    character: str
    series: str
    unique_code: str

class MinifigureResponse(BaseModel):
    id: int
    name: str
    character: str
    series: str
    unique_code: str
    
    class Config:
        from_attributes = True

# Theme schemas
class ThemeCreate(BaseModel):
    name: str
    description: str

class ThemeResponse(BaseModel):
    id: int
    name: str
    description: str
    
    class Config:
        from_attributes = True

# Age category schemas
class AgeCategoryCreate(BaseModel):
    name: str
    min_age: int
    max_age: int

class AgeCategoryResponse(BaseModel):
    id: int
    name: str
    min_age: int
    max_age: int
    
    class Config:
        from_attributes = True

# Part type schemas
class PartTypeCreate(BaseModel):
    name: str
    hierarchy_level: int

class PartTypeResponse(BaseModel):
    id: int
    name: str
    hierarchy_level: int
    
    class Config:
        from_attributes = True

# Operation result
class OperationResult(BaseModel):
    success: bool
    message: str
    node_id: Optional[int] = None
    product_id: Optional[int] = None

# Search results
class SetSearchResult(BaseModel):
    set_name: str
    catalog_number: str
    year: int
    price: float
    theme_name: str

class AgeSearchResult(BaseModel):
    set_name: str
    catalog_number: str
    min_age: int
    max_age: int
    price: float

class PartSearchResult(BaseModel):
    part_name: str
    color: str
    size: str
    type_name: str
    weight: float

# Set contents
class SetContent(BaseModel):
    item_type: str
    item_name: str
    quantity: int
    color: Optional[str] = None