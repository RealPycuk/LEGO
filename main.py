# main.py
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, Dict, Any

from config import config
from models import Base, Classificator, Theme, AgeCategory, PartType, Set, Part, Minifigure
from schemas import *
from lego_classifier import LegoClassifier

# Create engine
engine = create_engine(config.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="Lego Classifier API",
    description="API для управления классификатором Lego на PostgreSQL",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize classifier
classifier = LegoClassifier(engine)

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    """Инициализация при запуске"""
    print("Запуск Lego Classifier API на PostgreSQL...")
    # Загружаем тестовые данные если база пуста
    with SessionLocal() as db:
        count = db.query(Classificator).count()
        if count == 0:
            print("База данных пуста, загружаем тестовые данные...")
            classifier.load_test_data(db)

@app.get("/")
def root():
    return {
        "message": "Lego Classifier API",
        "version": "2.0.0",
        "database": "PostgreSQL",
        "docs": "/docs"
    }

# ==================== CATEGORIES ====================

@app.get("/categories", response_model=List[Dict[str, Any]])
def get_categories(db: Session = Depends(get_db)):
    """Получить все категории"""
    return classifier.get_all_categories(db)

@app.post("/categories", response_model=OperationResult)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """Создать новую категорию"""
    result = classifier.add_node(db, data.name, "промежуточный", data.parent_id, sort_order=data.sort_order)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/categories/subcategory", response_model=OperationResult)
def create_subcategory(data: SubcategoryCreate, db: Session = Depends(get_db)):
    """Создать подкатегорию"""
    parent_id = None
    if data.parent_name:
        parent = db.query(Classificator).filter(Classificator.название == data.parent_name).first()
        if not parent:
            raise HTTPException(status_code=404, detail=f"Родительская категория '{data.parent_name}' не найдена")
        parent_id = parent.id
    
    result = classifier.add_node(db, data.child_name, "промежуточный", parent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.put("/categories/{node_id}/move", response_model=OperationResult)
def move_category(node_id: int, data: MoveNode, db: Session = Depends(get_db)):
    """Переместить категорию"""
    result = classifier.move_node(db, node_id, data.new_parent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.delete("/categories/{node_id}", response_model=OperationResult)
def delete_category(node_id: int, db: Session = Depends(get_db)):
    """Удалить категорию"""
    result = classifier.delete_node(db, node_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.put("/categories/{parent_id}/reorder", response_model=OperationResult)
def reorder_children(parent_id: int, data: ReorderChildren, db: Session = Depends(get_db)):
    """Изменить порядок потомков"""
    result = classifier.reorder_children(db, parent_id, data.ordered_child_ids)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.put("/categories/{node_id}/base-unit", response_model=OperationResult)
def set_base_unit(node_id: int, data: SetBaseUnit, db: Session = Depends(get_db)):
    """Установить единицу измерения"""
    result = classifier.set_base_unit(db, node_id, data.base_ei_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/categories/{node_id}/descendants")
def get_descendants(node_id: int, db: Session = Depends(get_db)):
    """Получить всех потомков узла"""
    return classifier.get_descendants(db, node_id)

@app.get("/categories/{node_id}/ancestors")
def get_ancestors(node_id: int, db: Session = Depends(get_db)):
    """Получить всех родителей узла"""
    return classifier.get_ancestors(db, node_id)

@app.get("/categories/{node_id}/terminals")
def get_terminal_descendants(node_id: int, db: Session = Depends(get_db)):
    """Получить терминальные классы"""
    return classifier.get_terminal_descendants(db, node_id)

@app.get("/cycles")
def detect_cycles(db: Session = Depends(get_db)):
    """Диагностика циклов"""
    return classifier.detect_cycles(db)

# ==================== SEARCH ====================

@app.get("/search/theme", response_model=List[SetSearchResult])
def search_by_theme(theme: str = Query(..., description="Название тематики"), db: Session = Depends(get_db)):
    """Поиск наборов по тематике"""
    return classifier.search_by_theme(db, theme)

@app.get("/search/age", response_model=List[AgeSearchResult])
def search_by_age(age: int = Query(..., description="Возраст"), db: Session = Depends(get_db)):
    """Поиск наборов по возрасту"""
    return classifier.search_by_age(db, age)

@app.get("/search/part-type", response_model=List[PartSearchResult])
def search_by_part_type(part_type: str = Query(..., description="Тип детали"), db: Session = Depends(get_db)):
    """Поиск деталей по типу"""
    return classifier.search_by_part_type(db, part_type)

# ==================== SETS ====================

@app.get("/sets", response_model=List[Dict[str, Any]])
def get_all_sets(db: Session = Depends(get_db)):
    """Получить все наборы"""
    return classifier.get_all_sets(db)

@app.post("/sets", response_model=OperationResult)
def create_set(data: SetCreate, db: Session = Depends(get_db)):
    """Создать набор"""
    result = classifier.add_set(
        db, data.name, data.catalog_number, data.year, data.price,
        data.parts_count, data.age_category_id, data.theme_id, data.parent_id
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/sets/{set_id}/contents")
def get_set_contents(set_id: int, db: Session = Depends(get_db)):
    """Получить состав набора"""
    return classifier.get_set_contents(db, set_id)

# ==================== PARTS ====================

@app.get("/parts", response_model=List[Dict[str, Any]])
def get_all_parts(db: Session = Depends(get_db)):
    """Получить все детали"""
    return classifier.get_all_parts(db)

@app.post("/parts", response_model=OperationResult)
def create_part(data: PartCreate, db: Session = Depends(get_db)):
    """Создать деталь"""
    result = classifier.add_part(db, data.name, data.color, data.size, data.weight, data.part_type_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ==================== MINIFIGURES ====================

@app.get("/minifigures", response_model=List[Dict[str, Any]])
def get_all_minifigures(db: Session = Depends(get_db)):
    """Получить все мини-фигурки"""
    return classifier.get_all_minifigures(db)

@app.post("/minifigures", response_model=OperationResult)
def create_minifigure(data: MinifigureCreate, db: Session = Depends(get_db)):
    """Создать мини-фигурку"""
    result = classifier.add_minifigure(db, data.name, data.character, data.series, data.unique_code)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ==================== DIRECTORIES ====================

@app.get("/themes", response_model=List[ThemeResponse])
def get_themes(db: Session = Depends(get_db)):
    """Получить все тематики"""
    return classifier.get_all_themes(db)

@app.post("/themes", response_model=OperationResult)
def create_theme(data: ThemeCreate, db: Session = Depends(get_db)):
    """Создать тематику"""
    result = classifier.add_theme(db, data.name, data.description)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/age-categories", response_model=List[AgeCategoryResponse])
def get_age_categories(db: Session = Depends(get_db)):
    """Получить все возрастные категории"""
    return classifier.get_all_age_categories(db)

@app.post("/age-categories", response_model=OperationResult)
def create_age_category(data: AgeCategoryCreate, db: Session = Depends(get_db)):
    """Создать возрастную категорию"""
    result = classifier.add_age_category(db, data.name, data.min_age, data.max_age)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/part-types", response_model=List[PartTypeResponse])
def get_part_types(db: Session = Depends(get_db)):
    """Получить все типы деталей"""
    return classifier.get_all_part_types(db)

@app.post("/part-types", response_model=OperationResult)
def create_part_type(data: PartTypeCreate, db: Session = Depends(get_db)):
    """Создать тип детали"""
    result = classifier.add_part_type(db, data.name, data.hierarchy_level)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ==================== UTILITIES ====================

@app.post("/test-data")
def load_test_data(db: Session = Depends(get_db)):
    """Загрузить тестовые данные"""
    result = classifier.load_test_data(db)
    return result

@app.delete("/clear")
def clear_database(db: Session = Depends(get_db)):
    """Очистить базу данных"""
    classifier.clear_database(db)
    return {"success": True, "message": "База данных очищена"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
