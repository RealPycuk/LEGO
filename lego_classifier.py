# lego_classifier.py
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from models import Classificator, Theme, AgeCategory, PartType, Set, Part, Minifigure, SetPart, SetMinifigure, Enumeration, EnumValue


class LegoClassifier:
    def __init__(self, engine):
        self.engine = engine
    
    def check_unique_code(self, db: Session, code: str, exclude_id: Optional[int] = None) -> bool:
        """Проверка уникальности названия"""
        query = db.query(Classificator).filter(Classificator.название == code)
        if exclude_id:
            query = query.filter(Classificator.id != exclude_id)
        return query.count() == 0
    
    def check_cycle(self, db: Session, node_id: int, new_parent_id: int) -> bool:
        """Проверка на циклы при перемещении"""
        if new_parent_id is None:
            return False
        
        # Рекурсивный CTE запрос для PostgreSQL
        sql = text("""
            WITH RECURSIVE ancestors(id) AS (
                SELECT CAST(:new_parent_id AS INTEGER)
                UNION ALL
                SELECT родительский_id FROM классификатор 
                INNER JOIN ancestors ON классификатор.id = ancestors.id
                WHERE родительский_id IS NOT NULL
            )
            SELECT COUNT(*) FROM ancestors WHERE id = CAST(:node_id AS INTEGER)
        """)
        result = db.execute(sql, {"new_parent_id": new_parent_id, "node_id": node_id})
        return result.scalar() > 0
    
    def get_max_sort_order(self, db: Session, parent_id: Optional[int]) -> int:
        """Получение максимального порядка сортировки"""
        max_order = db.query(func.coalesce(func.max(Classificator.порядок_сортировки), 0)).filter(
            Classificator.родительский_id == parent_id
        ).scalar()
        return max_order or 0
    
    def add_node(self, db: Session, name: str, node_type: str, parent_id: Optional[int] = None,
                 base_ei: Optional[int] = None, sort_order: Optional[int] = None) -> Dict[str, Any]:
        """Добавление новой вершины"""
        if not self.check_unique_code(db, name):
            return {"success": False, "message": "Узел с таким именем уже существует", "node_id": None}
        
        if sort_order is None:
            sort_order = self.get_max_sort_order(db, parent_id) + 1
        
        try:
            new_node = Classificator(
                название=name,
                тип_элемента=node_type,
                родительский_id=parent_id,
                порядок_сортировки=sort_order,
                базовая_ед_измерения=base_ei
            )
            db.add(new_node)
            db.commit()
            db.refresh(new_node)
            return {"success": True, "message": "Узел успешно добавлен", "node_id": new_node.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}", "node_id": None}
    
    def move_node(self, db: Session, node_id: int, new_parent_id: Optional[int]) -> Dict[str, Any]:
        """Перемещение вершины"""
        node = db.query(Classificator).filter(Classificator.id == node_id).first()
        if not node:
            return {"success": False, "message": "Узел не найден"}
        
        if self.check_cycle(db, node_id, new_parent_id):
            return {"success": False, "message": "Невозможно переместить: это создаст цикл"}
        
        try:
            node.родительский_id = new_parent_id
            db.commit()
            return {"success": True, "message": "Узел успешно перемещен"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def delete_node(self, db: Session, node_id: int) -> Dict[str, Any]:
        """Удаление вершины"""
        # Проверка на наличие потомков
        children_count = db.query(Classificator).filter(Classificator.родительский_id == node_id).count()
        if children_count > 0:
            return {"success": False, "message": "Невозможно удалить: узел имеет потомков"}
        
        try:
            node = db.query(Classificator).filter(Classificator.id == node_id).first()
            if node:
                db.delete(node)
                db.commit()
                return {"success": True, "message": "Узел успешно удален"}
            return {"success": False, "message": "Узел не найден"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def reorder_children(self, db: Session, parent_id: int, ordered_child_ids: List[int]) -> Dict[str, Any]:
        """Изменение порядка потомков"""
        try:
            for idx, child_id in enumerate(ordered_child_ids, 1):
                child = db.query(Classificator).filter(
                    Classificator.id == child_id,
                    Classificator.родительский_id == parent_id
                ).first()
                if not child:
                    return {"success": False, "message": f"Узел {child_id} не является потомком узла {parent_id}"}
                child.порядок_сортировки = idx
            db.commit()
            return {"success": True, "message": "Порядок потомков успешно изменен"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def set_base_unit(self, db: Session, node_id: int, base_ei_id: int) -> Dict[str, Any]:
        """Установка базовой единицы измерения"""
        try:
            node = db.query(Classificator).filter(Classificator.id == node_id).first()
            if node:
                node.базовая_ед_измерения = base_ei_id
                db.commit()
                return {"success": True, "message": "Единица измерения успешно установлена"}
            return {"success": False, "message": "Узел не найден"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def get_descendants(self, db: Session, node_id: int) -> List[Dict[str, Any]]:
        """Поиск всех потомков"""
        sql = text("""
            WITH RECURSIVE descendants AS (
                SELECT id, название, тип_элемента, родительский_id, 0 as уровень, порядок_сортировки
                FROM классификатор WHERE id = :node_id
                UNION ALL
                SELECT c.id, c.название, c.тип_элемента, c.родительский_id, d.уровень + 1, c.порядок_сортировки
                FROM классификатор c INNER JOIN descendants d ON c.родительский_id = d.id
            )
            SELECT id, название, тип_элемента, родительский_id, уровень, порядок_сортировки
            FROM descendants WHERE id != :node_id ORDER BY уровень, порядок_сортировки, название
        """)
        result = db.execute(sql, {"node_id": node_id})
        return [dict(row._mapping) for row in result]
    
    def get_ancestors(self, db: Session, node_id: int) -> List[Dict[str, Any]]:
        """Поиск всех родителей"""
        sql = text("""
            WITH RECURSIVE ancestors AS (
                SELECT id, название, тип_элемента, родительский_id, 0 as уровень
                FROM классификатор WHERE id = :node_id
                UNION ALL
                SELECT c.id, c.название, c.тип_элемента, c.родительский_id, a.уровень + 1
                FROM классификатор c INNER JOIN ancestors a ON c.id = a.родительский_id
            )
            SELECT id, название, тип_элемента, родительский_id, уровень
            FROM ancestors WHERE id != :node_id ORDER BY уровень
        """)
        result = db.execute(sql, {"node_id": node_id})
        return [dict(row._mapping) for row in result]
    
    def get_terminal_descendants(self, db: Session, node_id: int) -> List[Dict[str, Any]]:
        """Поиск терминальных классов"""
        sql = text("""
            WITH RECURSIVE descendants AS (
                SELECT id, название, тип_элемента, родительский_id
                FROM классификатор WHERE id = :node_id
                UNION ALL
                SELECT c.id, c.название, c.тип_элемента, c.родительский_id
                FROM классификатор c INNER JOIN descendants d ON c.родительский_id = d.id
            )
            SELECT id, название, тип_элемента, родительский_id
            FROM descendants WHERE тип_элемента IN ('терминальный', 'набор') ORDER BY название
        """)
        result = db.execute(sql, {"node_id": node_id})
        return [dict(row._mapping) for row in result]
    
    def detect_cycles(self, db: Session) -> List[Dict[str, Any]]:
        """Диагностика циклов во всем классификаторе"""
        # Упрощенная проверка - ищем узлы, у которых родитель ссылается на потомка
        sql = text("""
            WITH RECURSIVE tree(id, root_id, path, depth) AS (
                SELECT id, id, название::text, 0 FROM классификатор
                UNION ALL
                SELECT tree.id, c.родительский_id, tree.path || ' -> ' || c.название, tree.depth + 1
                FROM tree JOIN классификатор c ON c.id = tree.root_id
                WHERE c.родительский_id IS NOT NULL AND tree.depth < 20
            )
            SELECT DISTINCT tree.id, к.название, tree.path
            FROM tree JOIN классификатор к ON к.id = tree.id
            WHERE tree.root_id = tree.id AND tree.depth > 0
        """)
        result = db.execute(sql)
        return [{"node_id": row[0], "node_name": row[1], "path": row[2]} for row in result]
    
    def add_set(self, db: Session, name: str, catalog_number: str, year: int, price: float,
                parts_count: int, age_category_id: int, theme_id: int, parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Добавление набора"""
        node_result = self.add_node(db, name, 'набор', parent_id)
        if not node_result["success"]:
            return node_result
        
        try:
            new_set = Set(
                id_классификатора=node_result["node_id"],
                номер_по_каталогу=catalog_number,
                год_выпуска=year,
                цена=price,
                количество_деталей=parts_count,
                id_возрастной_категории=age_category_id,
                id_тематики=theme_id
            )
            db.add(new_set)
            db.commit()
            db.refresh(new_set)
            return {"success": True, "message": "Набор успешно добавлен", "product_id": new_set.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}", "product_id": None}
    
    def add_part(self, db: Session, name: str, color: str, size: str, weight: float, part_type_id: int) -> Dict[str, Any]:
        """Добавление детали"""
        node_result = self.add_node(db, name, "терминальный", None)
        if not node_result["success"]:
            return node_result
        
        try:
            new_part = Part(
                id_классификатора=node_result["node_id"],
                цвет=color,
                размер=size,
                вес=weight,
                id_типа=part_type_id
            )
            db.add(new_part)
            db.commit()
            db.refresh(new_part)
            return {"success": True, "message": f"Деталь '{name}' добавлена", "product_id": new_part.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def add_minifigure(self, db: Session, name: str, character: str, series: str, unique_code: str) -> Dict[str, Any]:
        """Добавление мини-фигурки"""
        node_result = self.add_node(db, name, "терминальный", None)
        if not node_result["success"]:
            return node_result
        
        try:
            new_minifigure = Minifigure(
                id_классификатора=node_result["node_id"],
                персонаж=character,
                серия=series,
                уникальный_код=unique_code
            )
            db.add(new_minifigure)
            db.commit()
            db.refresh(new_minifigure)
            return {"success": True, "message": f"Мини-фигурка '{name}' добавлена", "product_id": new_minifigure.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def get_set_contents(self, db: Session, set_id: int) -> List[Dict[str, Any]]:
        """Получение состава набора"""
        sql = text("""
            SELECT 'Деталь' as item_type, кл.название as item_name, сн.количество_штук as quantity, д.цвет as color
            FROM набор н
            INNER JOIN состав_набора сн ON сн.id_набора = н.id
            INNER JOIN деталь д ON д.id = сн.id_детали
            INNER JOIN классификатор кл ON кл.id = д.id_классификатора
            WHERE н.id = :set_id
            UNION ALL
            SELECT 'Мини-фигурка' as item_type, кл.название as item_name, фвн.количество_штук as quantity, NULL as color
            FROM набор н
            INNER JOIN фигурки_в_наборе фвн ON фвн.id_набора = н.id
            INNER JOIN мини_фигурка мф ON мф.id = фвн.id_фигурки
            INNER JOIN классификатор кл ON кл.id = мф.id_классификатора
            WHERE н.id = :set_id
        """)
        result = db.execute(sql, {"set_id": set_id})
        return [dict(row._mapping) for row in result]
    
    def search_by_theme(self, db: Session, theme_name: str) -> List[Dict[str, Any]]:
        """Поиск по тематике"""
        sql = text("""
            SELECT кл.название as set_name, н.номер_по_каталогу as catalog_number,
                   н.год_выпуска as year, н.цена as price, тема_кл.название as theme_name
            FROM набор н
            JOIN классификатор кл ON кл.id = н.id_классификатора
            JOIN тематика т ON т.id = н.id_тематики
            JOIN классификатор тема_кл ON тема_кл.id = т.id_классификатора
            WHERE тема_кл.название LIKE '%' || :theme_name || '%'
            ORDER BY н.год_выпуска DESC
        """)
        result = db.execute(sql, {"theme_name": theme_name})
        return [dict(row._mapping) for row in result]
    
    def search_by_age(self, db: Session, age: int) -> List[Dict[str, Any]]:
        """Поиск по возрасту"""
        sql = text("""
            SELECT кл.название as set_name, н.номер_по_каталогу as catalog_number,
                   вк.минимальный_возраст as min_age, вк.максимальный_возраст as max_age, н.цена as price
            FROM набор н
            JOIN классификатор кл ON кл.id = н.id_классификатора
            JOIN возрастная_категория вк ON вк.id = н.id_возрастной_категории
            WHERE :age BETWEEN вк.минимальный_возраст AND вк.максимальный_возраст
            ORDER BY вк.минимальный_возраст
        """)
        result = db.execute(sql, {"age": age})
        return [dict(row._mapping) for row in result]
    
    def search_by_part_type(self, db: Session, type_name: str) -> List[Dict[str, Any]]:
        """Поиск по типу детали"""
        sql = text("""
            SELECT кл.название as part_name, д.цвет as color, д.размер as size,
                тип_кл.название as type_name, д.вес as weight
            FROM деталь д
            JOIN классификатор кл ON кл.id = д.id_классификатора
            JOIN тип_детали тд ON тд.id = д.id_типа
            JOIN классификатор тип_кл ON тип_кл.id = тд.id_классификатора
            WHERE тип_кл.название LIKE '%' || :type_name || '%'
            ORDER BY кл.название
        """)
        result = db.execute(sql, {"type_name": type_name})
        return [dict(row._mapping) for row in result]
    
    def get_all_categories(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех категорий"""
        categories = db.query(Classificator).order_by(Classificator.id).all()
        return [{
            "id": c.id,
            "name": c.название,
            "node_type": c.тип_элемента,
            "parent_id": c.родительский_id,
            "sort_order": c.порядок_сортировки
        } for c in categories]
    
    def get_all_sets(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех наборов"""
        sets = db.query(Set).join(Classificator, Classificator.id == Set.id_классификатора).all()
        return [{
            "id": s.id,
            "name": s.classificator.название,
            "catalog_number": s.номер_по_каталогу,
            "year": s.год_выпуска,
            "price": s.цена,
            "parts_count": s.количество_деталей
        } for s in sets]
    
    def get_all_parts(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех деталей"""
        parts = db.query(Part).join(Classificator, Classificator.id == Part.id_классификатора).all()
        return [{
            "id": p.id,
            "name": p.classificator.название,
            "color": p.цвет,
            "size": p.размер,
            "weight": p.вес,
            "part_type_id": p.id_типа
        } for p in parts]
    
    def get_all_minifigures(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех мини-фигурок"""
        minifigures = db.query(Minifigure).join(Classificator, Classificator.id == Minifigure.id_классификатора).all()
        return [{
            "id": m.id,
            "name": m.classificator.название,
            "character": m.персонаж,
            "series": m.серия,
            "unique_code": m.уникальный_код
        } for m in minifigures]
    
    def get_all_themes(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех тематик"""
        themes = db.query(Theme).join(Classificator, Classificator.id == Theme.id_классификатора).all()
        return [{
            "id": t.id,
            "name": t.classificator.название,
            "description": t.описание
        } for t in themes]
    
    def get_all_age_categories(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех возрастных категорий"""
        age_cats = db.query(AgeCategory).join(Classificator, Classificator.id == AgeCategory.id_классификатора).all()
        return [{
            "id": a.id,
            "name": a.classificator.название,
            "min_age": a.минимальный_возраст,
            "max_age": a.максимальный_возраст
        } for a in age_cats]
    
    def get_all_part_types(self, db: Session) -> List[Dict[str, Any]]:
        """Получение всех типов деталей"""
        part_types = db.query(PartType).join(Classificator, Classificator.id == PartType.id_классификатора).all()
        return [{
            "id": p.id,
            "name": p.classificator.название,
            "hierarchy_level": p.уровень_иерархии
        } for p in part_types]
    
    def add_theme(self, db: Session, name: str, description: str) -> Dict[str, Any]:
        """Добавление тематики"""
        node_result = self.add_node(db, name, "тематика", None)
        if not node_result["success"]:
            return node_result
        
        try:
            new_theme = Theme(
                id_классификатора=node_result["node_id"],
                описание=description
            )
            db.add(new_theme)
            db.commit()
            return {"success": True, "message": f"Тематика '{name}' добавлена", "node_id": node_result["node_id"]}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def add_age_category(self, db: Session, name: str, min_age: int, max_age: int) -> Dict[str, Any]:
        """Добавление возрастной категории"""
        node_result = self.add_node(db, name, "возрастная_категория", None)
        if not node_result["success"]:
            return node_result
        
        try:
            new_age_cat = AgeCategory(
                id_классификатора=node_result["node_id"],
                минимальный_возраст=min_age,
                максимальный_возраст=max_age
            )
            db.add(new_age_cat)
            db.commit()
            return {"success": True, "message": f"Возрастная категория '{name}' добавлена", "node_id": node_result["node_id"]}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    def add_part_type(self, db: Session, name: str, hierarchy_level: int) -> Dict[str, Any]:
        """Добавление типа детали"""
        node_result = self.add_node(db, name, "тип_детали", None)
        if not node_result["success"]:
            return node_result
        
        try:
            new_part_type = PartType(
                id_классификатора=node_result["node_id"],
                уровень_иерархии=hierarchy_level
            )
            db.add(new_part_type)
            db.commit()
            db.refresh(new_part_type)
            return {
                "success": True,
                "message": f"Тип детали '{name}' добавлен",
                "node_id": node_result["node_id"],
                "product_id": new_part_type.id,
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
        # ========== ПЕРЕЧИСЛЕНИЯ (ЗАДАНИЕ 1.2) ==========

    def add_enumeration(self, db: Session, name: str, description: str = None) -> Dict[str, Any]:
        """Создать новое перечисление"""
        exists = db.query(Enumeration).filter(Enumeration.name == name).first()
        if exists:
            return {"success": False, "message": f"Перечисление '{name}' уже существует"}
        try:
            enum = Enumeration(name=name, description=description)
            db.add(enum)
            db.commit()
            db.refresh(enum)
            return {"success": True, "message": "Перечисление создано", "enum_id": enum.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    def get_all_enumerations(self, db: Session) -> List[Dict[str, Any]]:
        """Получить все перечисления с количеством значений"""
        enums = db.query(Enumeration).all()
        result = []
        for e in enums:
            values_count = db.query(EnumValue).filter(EnumValue.enumeration_id == e.id).count()
            result.append({
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "created_at": e.created_at,
                "values_count": values_count
            })
        return result

    def get_enumeration_by_id(self, db: Session, enum_id: int) -> Dict[str, Any]:
        """Получить перечисление по ID"""
        enum = db.query(Enumeration).filter(Enumeration.id == enum_id).first()
        if not enum:
            return {"success": False, "message": "Перечисление не найдено"}
        return {
            "success": True,
            "id": enum.id,
            "name": enum.name,
            "description": enum.description,
            "created_at": enum.created_at
        }

    def update_enumeration(self, db: Session, enum_id: int, name: str = None, description: str = None) -> Dict[str, Any]:
        """Обновить перечисление"""
        enum = db.query(Enumeration).filter(Enumeration.id == enum_id).first()
        if not enum:
            return {"success": False, "message": "Перечисление не найдено"}
        try:
            if name is not None:
                enum.name = name
            if description is not None:
                enum.description = description
            db.commit()
            return {"success": True, "message": "Перечисление обновлено"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    def delete_enumeration(self, db: Session, enum_id: int) -> Dict[str, Any]:
        """Удалить перечисление (каскадно удалит все значения)"""
        enum = db.query(Enumeration).filter(Enumeration.id == enum_id).first()
        if not enum:
            return {"success": False, "message": "Перечисление не найдено"}
        try:
            db.delete(enum)
            db.commit()
            return {"success": True, "message": "Перечисление удалено"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    # ----- Значения перечислений -----

    def add_enum_value(self, db: Session, enum_id: int, value: str, sort_order: int = None, extra_data: dict = None) -> Dict[str, Any]:
        """Добавить значение в перечисление"""
        enum = db.query(Enumeration).filter(Enumeration.id == enum_id).first()
        if not enum:
            return {"success": False, "message": "Перечисление не найдено"}
        if sort_order is None:
            max_order = db.query(func.coalesce(func.max(EnumValue.sort_order), 0)).filter(EnumValue.enumeration_id == enum_id).scalar()
            sort_order = max_order + 1
        try:
            ev = EnumValue(enumeration_id=enum_id, value=value, sort_order=sort_order, extra_data=extra_data)
            db.add(ev)
            db.commit()
            db.refresh(ev)
            return {"success": True, "message": "Значение добавлено", "value_id": ev.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    def get_enum_values(self, db: Session, enum_id: int) -> List[Dict[str, Any]]:
        """Получить все значения перечисления (сортировка по sort_order)"""
        values = db.query(EnumValue).filter(EnumValue.enumeration_id == enum_id).order_by(EnumValue.sort_order).all()
        return [{"id": v.id, "value": v.value, "sort_order": v.sort_order, "extra_data": v.extra_data} for v in values]

    def update_enum_value(self, db: Session, value_id: int, value: str = None, sort_order: int = None, extra_data: dict = None) -> Dict[str, Any]:
        """Обновить значение перечисления"""
        ev = db.query(EnumValue).filter(EnumValue.id == value_id).first()
        if not ev:
            return {"success": False, "message": "Значение не найдено"}
        try:
            if value is not None:
                ev.value = value
            if sort_order is not None:
                ev.sort_order = sort_order
            if extra_data is not None:
                ev.extra_data = extra_data
            db.commit()
            return {"success": True, "message": "Значение обновлено"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    def reorder_enum_values(self, db: Session, enum_id: int, ordered_ids: List[int]) -> Dict[str, Any]:
        """Изменить порядок значений перечисления"""
        # Проверка, что все ID принадлежат этому перечислению
        for idx, vid in enumerate(ordered_ids, start=1):
            ev = db.query(EnumValue).filter(EnumValue.id == vid, EnumValue.enumeration_id == enum_id).first()
            if not ev:
                return {"success": False, "message": f"Значение {vid} не принадлежит перечислению {enum_id}"}
        try:
            for idx, vid in enumerate(ordered_ids, start=1):
                db.query(EnumValue).filter(EnumValue.id == vid).update({"sort_order": idx})
            db.commit()
            return {"success": True, "message": "Порядок значений изменён"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}

    def delete_enum_value(self, db: Session, value_id: int) -> Dict[str, Any]:
        """Удалить значение перечисления"""
        ev = db.query(EnumValue).filter(EnumValue.id == value_id).first()
        if not ev:
            return {"success": False, "message": "Значение не найдено"}
        try:
            db.delete(ev)
            db.commit()
            return {"success": True, "message": "Значение удалено"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": str(e)}
    
    def clear_database(self, db: Session):
        """Очистка базы данных"""
        db.query(SetMinifigure).delete()
        db.query(SetPart).delete()
        db.query(Minifigure).delete()
        db.query(Part).delete()
        db.query(Set).delete()
        db.query(PartType).delete()
        db.query(AgeCategory).delete()
        db.query(Theme).delete()
        db.query(Classificator).delete()
        db.query(Enumeration).delete()
        db.query(EnumValue).delete()
        db.commit()
        print("База данных очищена")
    
    def load_test_data(self, db: Session) -> Dict[str, Any]:
        """Загрузка тестовых данных"""
        self.clear_database(db)
        
        # 1. Тематика
        themes_data = [
            ("City", "Городская тематика"),
            ("Star Wars", "Звёздные войны"),
            ("Technic", "Техник"),
            ("Botanical collection", "Ботаническая коллекция"),
            ("Harry Potter", "Гарри Поттер"),
            ("Marvel", "Марвел"),
            ("Creator", "Творец")
        ]
        for name, desc in themes_data:
            self.add_theme(db, name, desc)
        
        # 2. Возрастные категории
        age_data = [
            ("2-4 лет", 2, 4),
            ("4-6 лет", 4, 6),
            ("6-13 лет", 6, 13),
            ("14-18 лет", 14, 18),
            ("18+ лет", 18, 99)
        ]
        for name, min_age, max_age in age_data:
            self.add_age_category(db, name, min_age, max_age)
        
        # 3. Корневой элемент
        root_result = self.add_node(db, "Изделия бренда LEGO", "промежуточный", None, sort_order=1)
        root_id = root_result["node_id"]
        
        # 4. Основные категории
        sets_result = self.add_node(db, "Наборы", "промежуточный", root_id, sort_order=1)
        parts_result = self.add_node(db, "Детали", "промежуточный", root_id, sort_order=2)
        minifigs_result = self.add_node(db, "Мини-фигурки", "промежуточный", root_id, sort_order=3)
        
        sets_id = sets_result["node_id"]
        parts_id = parts_result["node_id"]
        
        # 5. Подкатегории наборов
        self.add_node(db, "Тематика City", "промежуточный", sets_id, sort_order=1)
        self.add_node(db, "Тематика Star Wars", "промежуточный", sets_id, sort_order=2)
        self.add_node(db, "Тематика Technic", "промежуточный", sets_id, sort_order=3)
        
        # 6. Подкатегории деталей
        bricks_id = self.add_node(db, "Кирпичи", "промежуточный", parts_id, sort_order=1)["node_id"]
        plates_id = self.add_node(db, "Плиты", "промежуточный", parts_id, sort_order=2)["node_id"]
        self.add_node(db, "Технические детали", "промежуточный", parts_id, sort_order=3)
        special_id = self.add_node(db, "Специальные детали", "промежуточный", parts_id, sort_order=4)["node_id"]
        
        # 7. Терминальные узлы деталей
        brick_2x4_id = self.add_node(db, "Кирпич 2x4", "терминальный", bricks_id, sort_order=1)["node_id"]
        brick_2x2_id = self.add_node(db, "Кирпич 2x2", "терминальный", bricks_id, sort_order=2)["node_id"]
        plate_1x2_id = self.add_node(db, "Плита 1x2", "терминальный", plates_id, sort_order=1)["node_id"]
        self.add_node(db, "Плита 2x4", "терминальный", plates_id, sort_order=2)
        wheel_id = self.add_node(db, "Колесо", "терминальный", special_id, sort_order=1)["node_id"]
        
        # 8. Типы деталей
        brick_type = self.add_part_type(db, "Кирпич", 1)
        plate_type = self.add_part_type(db, "Плита", 1)
        self.add_part_type(db, "Техническая", 1)
        special_type = self.add_part_type(db, "Специальная", 1)
        
        brick_type_id = brick_type["product_id"]
        plate_type_id = plate_type["product_id"]
        special_type_id = special_type["product_id"]
        
        # 9. Получение ID справочников
        star_wars_theme = db.query(Theme).join(Classificator).filter(Classificator.название == "Star Wars").first()
        city_theme = db.query(Theme).join(Classificator).filter(Classificator.название == "City").first()
        technic_theme = db.query(Theme).join(Classificator).filter(Classificator.название == "Technic").first()
        
        age_14 = db.query(AgeCategory).filter(AgeCategory.минимальный_возраст == 14).first()
        age_6 = db.query(AgeCategory).filter(AgeCategory.минимальный_возраст == 6).first()
        
        # 10. Добавление наборов
        self.add_set(db, "Звезда Смерти", "75159", 2020, 499.99, 4016, age_14.id, star_wars_theme.id, sets_id)
        self.add_set(db, "Космический корабль", "75257", 2019, 159.99, 1351, age_6.id, star_wars_theme.id, sets_id)
        self.add_set(db, "Полицейский участок", "60266", 2020, 129.99, 745, age_6.id, city_theme.id, sets_id)
        self.add_set(db, "Внедорожник", "42110", 2019, 199.99, 2573, age_14.id, technic_theme.id, sets_id)
        
        # 11. Добавление деталей
        self.add_part(db, "Кирпич 2x4 красный", "Красный", "2x4", 2.5, brick_type_id)
        self.add_part(db, "Кирпич 2x4 синий", "Синий", "2x4", 2.5, brick_type_id)
        self.add_part(db, "Кирпич 2x2 зелёный", "Зелёный", "2x2", 1.2, brick_type_id)
        self.add_part(db, "Плита 1x2 белая", "Белый", "1x2", 0.8, plate_type_id)
        self.add_part(db, "Колесо чёрное", "Чёрный", "30x14", 5.0, special_type_id)
        
        # 12. Добавление мини-фигурок
        self.add_minifigure(db, "Люк Скайуокер", "Люк", "Star Wars", "SW001")
        self.add_minifigure(db, "Дарт Вейдер", "Дарт Вейдер", "Star Wars", "SW002")
        self.add_minifigure(db, "Полицейский", "Полицейский", "City", "CT001")
        
        # 13. Добавление связей набор-деталь и набор-фигурка
        death_star = db.query(Set).join(Classificator).filter(Classificator.название == "Звезда Смерти").first()
        spaceship = db.query(Set).join(Classificator).filter(Classificator.название == "Космический корабль").first()
        
        red_brick = db.query(Part).join(Classificator).filter(Classificator.название == "Кирпич 2x4 красный").first()
        blue_brick = db.query(Part).join(Classificator).filter(Classificator.название == "Кирпич 2x4 синий").first()
        green_brick = db.query(Part).join(Classificator).filter(Classificator.название == "Кирпич 2x2 зелёный").first()
        white_plate = db.query(Part).join(Classificator).filter(Classificator.название == "Плита 1x2 белая").first()
        wheel = db.query(Part).join(Classificator).filter(Classificator.название == "Колесо чёрное").first()
        
        luke = db.query(Minifigure).filter(Minifigure.уникальный_код == "SW001").first()
        vader = db.query(Minifigure).filter(Minifigure.уникальный_код == "SW002").first()
        
        # Связи для Звезды Смерти
        db.add(SetPart(id_набора=death_star.id, id_детали=red_brick.id, количество_штук=50))
        db.add(SetPart(id_набора=death_star.id, id_детали=blue_brick.id, количество_штук=30))
        db.add(SetPart(id_набора=death_star.id, id_детали=green_brick.id, количество_штук=40))
        db.add(SetPart(id_набора=death_star.id, id_детали=white_plate.id, количество_штук=100))
        
        db.add(SetMinifigure(id_набора=death_star.id, id_фигурки=luke.id, количество_штук=2))
        db.add(SetMinifigure(id_набора=death_star.id, id_фигурки=vader.id, количество_штук=1))
        
        # Связи для Космического корабля
        db.add(SetPart(id_набора=spaceship.id, id_детали=red_brick.id, количество_штук=20))
        db.add(SetPart(id_набора=spaceship.id, id_детали=green_brick.id, количество_штук=15))
        db.add(SetPart(id_набора=spaceship.id, id_детали=wheel.id, количество_штук=4))
        
        db.add(SetMinifigure(id_набора=spaceship.id, id_фигурки=luke.id, количество_штук=1))
        
        db.commit()

        # ========== ПЕРЕЧИСЛЕНИЯ ==========
        print("  Добавляем тестовые перечисления...")
        
        # Перечисление "Тип детали"
        enum_part_type = self.add_enumeration(db, "Тип детали", "Типы деталей LEGO")
        if enum_part_type["success"]:
            enum_id = enum_part_type["enum_id"]
            self.add_enum_value(db, enum_id, "Кирпич", 1)
            self.add_enum_value(db, enum_id, "Плита", 2)
            self.add_enum_value(db, enum_id, "Техническая", 3)
            self.add_enum_value(db, enum_id, "Специальная", 4)
        else:
            print(f"    Ошибка: {enum_part_type['message']}")
        
        # Перечисление "Цвет детали"
        enum_color = self.add_enumeration(db, "Цвет детали", "Цвета деталей LEGO")
        if enum_color["success"]:
            enum_id = enum_color["enum_id"]
            self.add_enum_value(db, enum_id, "Красный", 1)
            self.add_enum_value(db, enum_id, "Синий", 2)
            self.add_enum_value(db, enum_id, "Зелёный", 3)
            self.add_enum_value(db, enum_id, "Белый", 4)
            self.add_enum_value(db, enum_id, "Чёрный", 5)
        else:
            print(f"    Ошибка: {enum_color['message']}")
        
        # Перечисление "Редкость мини-фигурки"
        enum_rarity = self.add_enumeration(db, "Редкость", "Редкость мини-фигурок")
        if enum_rarity["success"]:
            enum_id = enum_rarity["enum_id"]
            self.add_enum_value(db, enum_id, "Common", 1)
            self.add_enum_value(db, enum_id, "Rare", 2)
            self.add_enum_value(db, enum_id, "Exclusive", 3)
        else:
            print(f"    Ошибка: {enum_rarity['message']}")
        
        db.commit()
        print("  Тестовые перечисления добавлены")
        
        return {"success": True, "message": "Тестовые данные успешно загружены"}
