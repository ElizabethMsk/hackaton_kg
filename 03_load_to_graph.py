"""
Загрузка сущностей в Neo4j с проверками безопасности.
Версия 2.0 — исправлены уязвимости CodeQL.
"""
from neo4j import GraphDatabase
import json
import os
import sys
import logging
from typing import List, Dict, Optional



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# БЕЗОПАСНАЯ ЗАГРУЗКА КОНФИГА (без exec!)

def load_config(config_path: str) -> dict:
    """Безопасно загружает JSON-конфиг"""
    if not os.path.exists(config_path):
        logger.error(f"Конфиг не найден: {config_path}")
        logger.error("Создайте файл ml/config.json")
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f" Конфиг загружен: {config_path}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f" Ошибка парсинга JSON: {e}")
        raise
    except Exception as e:
        logger.error(f" Ошибка чтения конфига: {e}")
        raise


# ВАЛИДАЦИЯ: ALLOWLIST ДЛЯ LABELS И ТИПОВ СВЯЗЕЙ

ALLOWED_LABELS = {
    "ORG", "PER", "LOC", "DATE", "MONEY",
    "MATERIAL", "ALLOY", "PROCESS", "EQUIPMENT",
    "PROPERTY", "PROPERTY_VALUE", "TEMPERATURE",
    "NUMERIC_CONSTRAINT", "GEO_RU", "GEO_INTL",
    "DOCUMENT", "EXPERIMENT", "RESEARCHER", "LAB"
}

ALLOWED_RELATIONSHIPS = {
    "USED_IN", "REQUIRES", "AFFECTS", "RESULTS_IN",
    "EMPLOYS", "CONTAINS", "DESCRIBED_IN", "VALIDATED_BY",
    "PRODUCES", "MEASURED_BY", "LOCATED_IN", "RELATED_TO"
}

def sanitize_label(label: str) -> str:
    """Валидирует label через allowlist"""
    clean = label.replace(" ", "_").upper()
    if clean not in ALLOWED_LABELS:
        logger.warning(f"  Неизвестный label '{label}', использую 'UNKNOWN'")
        return "UNKNOWN"
    return clean

def sanitize_relationship(rel_type: str) -> Optional[str]:
    """Валидирует тип связи через allowlist"""
    clean = rel_type.replace(" ", "_").upper()
    if clean not in ALLOWED_RELATIONSHIPS:
        return None
    return clean


# ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ

def validate_entity(entity: dict) -> bool:
    """Проверяет структуру сущности"""
    if not isinstance(entity, dict):
        return False
    if "text" not in entity or "label" not in entity:
        return False
    if not isinstance(entity["text"], str) or not entity["text"].strip():
        return False
    if not isinstance(entity["label"], str):
        return False
    return True

# РАБОТА С NEO4J

def create_entity(tx, text: str, label: str):
    """Создаёт узел с валидированным label"""
    safe_label = sanitize_label(label)
    # Используем параметризованный запрос — текст передаётся через $text
    query = f"MERGE (n:{safe_label} {{name: $text}}) RETURN n"
    tx.run(query, text=text)

def create_relationship(tx, from_text: str, to_text: str, rel_type: str):
    """Создаёт связь с валидированным типом"""
    safe_rel = sanitize_relationship(rel_type)
    if safe_rel is None:
        return False
    # Текст передаётся параметризованно, тип связи — через allowlist
    query = f"""
    MATCH (a), (b)
    WHERE a.name = $from_text AND b.name = $to_text
    MERGE (a)-[r:{safe_rel}]->(b)
    RETURN r
    """
    tx.run(query, from_text=from_text, to_text=to_text)
    return True


# ОПРЕДЕЛЕНИЕ ТИПА СВЯЗИ (улучшенная логика)

def determine_relationship_type(label1: str, label2: str) -> Optional[str]:
    """Определяет тип связи между двумя сущностями"""
    rules = [
        ({"MATERIAL", "ALLOY"}, {"PROCESS", "TEMPERATURE"}, "USED_IN"),
        ({"PROCESS"}, {"EQUIPMENT"}, "REQUIRES"),
        ({"PROCESS"}, {"PROPERTY", "PROPERTY_VALUE"}, "AFFECTS"),
        ({"TEMPERATURE"}, {"PROPERTY_VALUE"}, "RESULTS_IN"),
        ({"ORG"}, {"PER"}, "EMPLOYS"),
        ({"LOC"}, {"ORG"}, "CONTAINS"),
        ({"MATERIAL"}, {"PROPERTY"}, "HAS_PROPERTY"),
        ({"EQUIPMENT"}, {"PROPERTY_VALUE"}, "MEASURED_BY"),
    ]
    
    for set1, set2, rel_type in rules:
        if label1 in set1 and label2 in set2:
            return rel_type
    return None


# ГЛАВНАЯ ФУНКЦИЯ
def main():
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ В NEO4J (БЕЗОПАСНАЯ ВЕРСИЯ)")
    print("=" * 70)
    
    # 1. Загрузка конфига
    print("\n[1/5] Загрузка конфигурации...")
    config_path = os.path.join(os.path.dirname(__file__), 'ml', 'config.json')
    try:
        config = load_config(config_path)
        neo4j_config = config["neo4j"]
    except Exception as e:
        logger.error(f"Не удалось загрузить конфиг: {e}")
        sys.exit(1)
    
    # 2. Подключение к Neo4j
    print("\n[2/5] Подключение к Neo4j...")
    try:
        driver = GraphDatabase.driver(
            neo4j_config["uri"],
            auth=(neo4j_config["user"], neo4j_config["password"])
        )
        driver.verify_connectivity()
        logger.info(" Подключение к Neo4j успешно")
    except Exception as e:
        logger.error(f" Ошибка подключения: {e}")
        logger.error("Проверьте, что Neo4j запущен и пароль верный")
        sys.exit(1)
    
    # 3. Чтение entities.json с валидацией
    print("\n[3/5] Чтение и валидация entities.json...")
    entities_file = os.path.join(os.path.dirname(__file__), 'entities.json')
    
    if not os.path.exists(entities_file):
        logger.error(" Файл entities.json не найден")
        logger.error("Сначала запустите: python 02_ner.py")
        sys.exit(1)
    
    try:
        with open(entities_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f" Невалидный JSON: {e}")
        sys.exit(1)
    
    # Валидация структуры
    valid_entities = []
    invalid_count = 0
    for i, ent in enumerate(entities):
        if validate_entity(ent):
            valid_entities.append(ent)
        else:
            invalid_count += 1
            if invalid_count <= 5:
                logger.warning(f"️  Пропущена невалидная сущность #{i}: {ent}")
    
    if invalid_count > 0:
        logger.warning(f"  Пропущено невалидных сущностей: {invalid_count}")
    
    logger.info(f" Валидных сущностей: {len(valid_entities)}/{len(entities)}")
    
    # 4. Загрузка узлов
    print(f"\n[4/5] Загрузка {len(valid_entities)} сущностей в Neo4j...")
    nodes_created = 0
    errors = 0
    
    with driver.session() as session:
        for i, ent in enumerate(valid_entities):
            try:
                session.execute_write(create_entity, ent["text"], ent["label"])
                nodes_created += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"  Прогресс: {i + 1}/{len(valid_entities)}")
            except Exception as e:
                errors += 1
                if errors <= 10:
                    logger.warning(f"   Ошибка с '{ent['text'][:50]}': {str(e)[:100]}")
    
    logger.info(f" Создано узлов: {nodes_created}")
    if errors > 0:
        logger.warning(f"️  Ошибок при создании узлов: {errors}")
    
    # 5. Создание связей (улучшенная логика)
    print("\n[5/5] Создание связей между сущностями...")
    relationships_created = 0
    relationship_stats = {}
    skipped_relationships = 0
    
    with driver.session() as session:
        for i in range(len(valid_entities) - 1):
            ent1 = valid_entities[i]
            ent2 = valid_entities[i + 1]
            
            rel_type = determine_relationship_type(ent1["label"], ent2["label"])
            
            if rel_type is None:
                skipped_relationships += 1
                continue
            
            try:
                success = session.execute_write(
                    create_relationship,
                    ent1["text"],
                    ent2["text"],
                    rel_type
                )
                if success:
                    relationships_created += 1
                    relationship_stats[rel_type] = relationship_stats.get(rel_type, 0) + 1
            except Exception as e:
                logger.debug(f"  Ошибка связи: {e}")
    
    logger.info(f" Создано связей: {relationships_created}")
    logger.info(f"️  Пропущено (нет подходящего типа): {skipped_relationships}")
    
    if relationship_stats:
        print("\n Статистика типов связей:")
        for rel_type, count in sorted(relationship_stats.items(), key=lambda x: -x[1]):
            print(f"   {rel_type}: {count}")
    
    # Завершение
    driver.close()
    
    print("\n" + "=" * 70)
    print(" ГОТОВО!")
    print("=" * 70)
    print(f"\n Итоговая статистика:")
    print(f"   Узлов создано: {nodes_created}")
    print(f"   Связей создано: {relationships_created}")
    print(f"   Ошибок: {errors}")
    print(f"\n Откройте Neo4j Browser: http://localhost:7474")
    print("   MATCH (n) RETURN n LIMIT 50")
    print("   MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 20")

if __name__ == "__main__":
    main()