from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import config
from lego_classifier import LegoClassifier
from models import (
    AgeCategory,
    Base,
    Classificator,
    Minifigure,
    Part,
    Set,
    SetMinifigure,
    SetPart,
    Theme,
)


engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_theme_id(db, theme_name: str) -> int:
    theme = (
        db.query(Theme)
        .join(Classificator)
        .filter(Classificator.название == theme_name)
        .first()
    )
    return theme.id


def get_age_category_id(db, min_age: int) -> int:
    category = (
        db.query(AgeCategory)
        .filter(AgeCategory.минимальный_возраст == min_age)
        .first()
    )
    if category is None:
        category = (
            db.query(AgeCategory)
            .filter(
                AgeCategory.минимальный_возраст <= min_age,
                AgeCategory.максимальный_возраст >= min_age,
            )
            .order_by(AgeCategory.минимальный_возраст.desc())
            .first()
        )
    return category.id


def get_set_id(db, set_name: str) -> int:
    product_set = (
        db.query(Set)
        .join(Classificator)
        .filter(Classificator.название == set_name)
        .first()
    )
    return product_set.id


def get_part_id(db, part_name: str) -> int:
    part = (
        db.query(Part)
        .join(Classificator)
        .filter(Classificator.название == part_name)
        .first()
    )
    return part.id


def get_minifigure_id(db, unique_code: str) -> int:
    minifigure = (
        db.query(Minifigure)
        .filter(Minifigure.уникальный_код == unique_code)
        .first()
    )
    return minifigure.id


def seed_swagger_data() -> None:
    Base.metadata.create_all(bind=engine)
    classifier = LegoClassifier(engine)

    with SessionLocal() as db:
        classifier.clear_database(db)

        themes = [
            ("City", "Городская серия: полиция, пожарные, транспорт и здания"),
            ("Star Wars", "Наборы по вселенной Star Wars"),
            ("Technic", "Сложные инженерные модели LEGO Technic"),
            ("Botanical Collection", "Декоративные растения и цветочные композиции"),
            ("Harry Potter", "Наборы по вселенной Гарри Поттера"),
            ("Marvel", "Супергеройские наборы Marvel"),
            ("Creator", "Наборы 3-в-1 и универсальные модели"),
            ("Ninjago", "Боевые наборы и драконы LEGO Ninjago"),
            ("Friends", "Повседневные сцены и здания LEGO Friends"),
        ]
        for name, description in themes:
            classifier.add_theme(db, name, description)

        age_categories = [
            ("2-4 лет", 2, 4),
            ("4-6 лет", 4, 6),
            ("6-8 лет", 6, 8),
            ("8-12 лет", 8, 12),
            ("12-16 лет", 12, 16),
            ("16-18 лет", 16, 18),
            ("18+ лет", 18, 99),
        ]
        for name, min_age, max_age in age_categories:
            classifier.add_age_category(db, name, min_age, max_age)

        root_id = classifier.add_node(
            db,
            "Изделия бренда LEGO",
            "промежуточный",
            None,
            sort_order=1,
        )["node_id"]

        sets_root_id = classifier.add_node(
            db, "Наборы", "промежуточный", root_id, sort_order=1
        )["node_id"]
        parts_root_id = classifier.add_node(
            db, "Детали", "промежуточный", root_id, sort_order=2
        )["node_id"]
        classifier.add_node(
            db, "Мини-фигурки", "промежуточный", root_id, sort_order=3
        )

        classifier.add_node(db, "Городские наборы", "промежуточный", sets_root_id, sort_order=1)
        classifier.add_node(db, "Фантастика", "промежуточный", sets_root_id, sort_order=2)
        classifier.add_node(db, "Инженерные модели", "промежуточный", sets_root_id, sort_order=3)
        classifier.add_node(db, "Коллекционные наборы", "промежуточный", sets_root_id, sort_order=4)

        bricks_id = classifier.add_node(
            db, "Кирпичи", "промежуточный", parts_root_id, sort_order=1
        )["node_id"]
        plates_id = classifier.add_node(
            db, "Плиты", "промежуточный", parts_root_id, sort_order=2
        )["node_id"]
        slopes_id = classifier.add_node(
            db, "Скосы", "промежуточный", parts_root_id, sort_order=3
        )["node_id"]
        technic_parts_id = classifier.add_node(
            db, "Technic детали", "промежуточный", parts_root_id, sort_order=4
        )["node_id"]
        special_parts_id = classifier.add_node(
            db, "Специальные детали", "промежуточный", parts_root_id, sort_order=5
        )["node_id"]

        classifier.add_node(db, "Кирпич 2x4", "терминальный", bricks_id, sort_order=1)
        classifier.add_node(db, "Кирпич 2x2", "терминальный", bricks_id, sort_order=2)
        classifier.add_node(db, "Плита 1x2", "терминальный", plates_id, sort_order=1)
        classifier.add_node(db, "Плита 2x4", "терминальный", plates_id, sort_order=2)
        classifier.add_node(db, "Скос 2x2", "терминальный", slopes_id, sort_order=1)
        classifier.add_node(db, "Ось Technic", "терминальный", technic_parts_id, sort_order=1)
        classifier.add_node(db, "Шестерня Technic", "терминальный", technic_parts_id, sort_order=2)
        classifier.add_node(db, "Колесо", "терминальный", special_parts_id, sort_order=1)
        classifier.add_node(db, "Прозрачный купол", "терминальный", special_parts_id, sort_order=2)

        brick_type_id = classifier.add_part_type(db, "Кирпич", 1)["product_id"]
        plate_type_id = classifier.add_part_type(db, "Плита", 1)["product_id"]
        slope_type_id = classifier.add_part_type(db, "Скос", 1)["product_id"]
        technic_type_id = classifier.add_part_type(db, "Technic-тип", 1)["product_id"]
        special_type_id = classifier.add_part_type(db, "Специальная", 1)["product_id"]

        sets_data = [
            ("Полицейский участок", "60246", 2021, 139.99, 668, 6, "City"),
            ("Пожарная станция", "60320", 2022, 89.99, 540, 6, "City"),
            ("Истребитель X-Wing", "75355", 2023, 239.99, 1949, 18, "Star Wars"),
            ("Шлем Дарта Вейдера", "75304", 2021, 79.99, 834, 18, "Star Wars"),
            ("Bugatti Bolide", "42151", 2023, 49.99, 905, 8, "Technic"),
            ("Букет цветов", "10280", 2021, 59.99, 756, 18, "Botanical Collection"),
            ("Замок Хогвартс", "76419", 2023, 169.99, 2660, 16, "Harry Potter"),
            ("Башня Мстителей", "76269", 2023, 499.99, 5201, 18, "Marvel"),
            ("Дракон стихий", "71793", 2023, 109.99, 1038, 8, "Ninjago"),
            ("Кафе на пляже", "41709", 2022, 39.99, 445, 6, "Friends"),
            ("Тигр 3-в-1", "31129", 2022, 49.99, 755, 9, "Creator"),
        ]
        for name, catalog_number, year, price, parts_count, min_age, theme_name in sets_data:
            classifier.add_set(
                db,
                name,
                catalog_number,
                year,
                price,
                parts_count,
                get_age_category_id(db, min_age),
                get_theme_id(db, theme_name),
                sets_root_id,
            )

        parts_data = [
            ("Кирпич 2x4 красный", "Красный", "2x4", 2.5, brick_type_id),
            ("Кирпич 2x4 синий", "Синий", "2x4", 2.5, brick_type_id),
            ("Кирпич 2x2 жёлтый", "Жёлтый", "2x2", 1.4, brick_type_id),
            ("Плита 1x2 белая", "Белый", "1x2", 0.8, plate_type_id),
            ("Плита 2x4 серый металлик", "Серый", "2x4", 1.6, plate_type_id),
            ("Скос 2x2 чёрный", "Чёрный", "2x2", 1.1, slope_type_id),
            ("Ось Technic чёрная", "Чёрный", "5L", 0.6, technic_type_id),
            ("Шестерня Technic серая", "Серый", "24T", 1.9, technic_type_id),
            ("Колесо внедорожное", "Чёрный", "49.5x20", 5.8, special_type_id),
            ("Прозрачный купол синий", "Прозрачный синий", "6x6x3", 3.2, special_type_id),
        ]
        for name, color, size, weight, part_type_id in parts_data:
            classifier.add_part(db, name, color, size, weight, part_type_id)

        minifigures_data = [
            ("Люк Скайуокер", "Люк", "Star Wars", "SW100"),
            ("Дарт Вейдер", "Дарт Вейдер", "Star Wars", "SW101"),
            ("Железный человек", "Тони Старк", "Marvel", "MV100"),
            ("Доктор Стрэндж", "Стивен Стрэндж", "Marvel", "MV101"),
            ("Гарри Поттер", "Гарри", "Harry Potter", "HP100"),
            ("Пожарный", "Пожарный", "City", "CT100"),
            ("Полицейский", "Полицейский", "City", "CT101"),
            ("Ниндзя Ллойд", "Ллойд", "Ninjago", "NJ100"),
            ("Подруга на пляже", "Нова", "Friends", "FR100"),
        ]
        for name, character, series, unique_code in minifigures_data:
            classifier.add_minifigure(db, name, character, series, unique_code)

        set_parts = [
            ("Полицейский участок", "Кирпич 2x4 красный", 25),
            ("Полицейский участок", "Плита 1x2 белая", 40),
            ("Пожарная станция", "Кирпич 2x2 жёлтый", 18),
            ("Пожарная станция", "Колесо внедорожное", 4),
            ("Истребитель X-Wing", "Кирпич 2x4 синий", 12),
            ("Истребитель X-Wing", "Прозрачный купол синий", 1),
            ("Bugatti Bolide", "Ось Technic чёрная", 12),
            ("Bugatti Bolide", "Шестерня Technic серая", 8),
            ("Башня Мстителей", "Кирпич 2x4 красный", 35),
            ("Башня Мстителей", "Плита 2x4 серый металлик", 28),
            ("Дракон стихий", "Скос 2x2 чёрный", 16),
            ("Тигр 3-в-1", "Кирпич 2x2 жёлтый", 22),
            ("Кафе на пляже", "Плита 1x2 белая", 14),
            ("Кафе на пляже", "Прозрачный купол синий", 2),
        ]
        for set_name, part_name, quantity in set_parts:
            db.add(
                SetPart(
                    id_набора=get_set_id(db, set_name),
                    id_детали=get_part_id(db, part_name),
                    количество_штук=quantity,
                )
            )

        set_minifigures = [
            ("Полицейский участок", "CT101", 2),
            ("Пожарная станция", "CT100", 2),
            ("Истребитель X-Wing", "SW100", 1),
            ("Шлем Дарта Вейдера", "SW101", 1),
            ("Башня Мстителей", "MV100", 1),
            ("Башня Мстителей", "MV101", 1),
            ("Замок Хогвартс", "HP100", 1),
            ("Дракон стихий", "NJ100", 1),
            ("Кафе на пляже", "FR100", 2),
        ]
        for set_name, unique_code, quantity in set_minifigures:
            db.add(
                SetMinifigure(
                    id_набора=get_set_id(db, set_name),
                    id_фигурки=get_minifigure_id(db, unique_code),
                    количество_штук=quantity,
                )
            )

        db.commit()

        print("База успешно заполнена тестовыми данными для Swagger UI.")
        print(f"Тематики: {db.query(Theme).count()}")
        print(f"Возрастные категории: {db.query(AgeCategory).count()}")
        print(f"Типы деталей: {db.query(Classificator).filter(Classificator.тип_элемента == 'тип_детали').count()}")
        print(f"Наборы: {db.query(Set).count()}")
        print(f"Детали: {db.query(Part).count()}")
        print(f"Мини-фигурки: {db.query(Minifigure).count()}")


if __name__ == "__main__":
    seed_swagger_data()
