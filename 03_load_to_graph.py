from neo4j import GraphDatabase
import json
import os

print("=" * 60)
print("ЗАГРУЗКА ДАННЫХ В NEO4J")
print("=" * 60)

# ============================================================
# 1. Подключение к Neo4j
# ============================================================
print("\n[1/4] Подключение к Neo4j...")

# Пробуем загрузить конфиг, если нет — используем значения по умолчанию
try:
    config_path = os.path.join(os.path.dirname(__file__), 'ml', 'config.py')
    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        exec(f.read(), config)
    
    NEO4J_URI = config.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = config.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = config.get('NEO4J_PASSWORD', 'test1234')
    print(f"   Конфиг загружен из ml/config.py")
except Exception as e:
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "test1234"
    print(f"   ⚠️  Используем настройки по умолчанию")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Проверяем подключение
    driver.verify_connectivity()
    print("   ✅ Подключение успешно!")
except Exception as e:
    print(f"   ❌ Ошибка подключения к Neo4j: {e}")
    print("   Убедитесь, что Neo4j запущен и пароль верный")
    exit(1)

# ============================================================
# 2. Чтение entities.json
# ============================================================
print("\n[2/4] Чтение entities.json...")

if not os.path.exists("entities.json"):
    print("   ❌ Файл entities.json не найден!")
    print("   Сначала запустите: python 02_ner.py")
    exit(1)

try:
    with open("entities.json", "r", encoding="utf-8") as f:
        entities = json.load(f)
    print(f"   ✅ Прочитано {len(entities)} сущностей")
except Exception as e:
    print(f"   ❌ Ошибка чтения файла: {e}")
    exit(1)

# ============================================================
# 3. Функции для работы с графом
# ============================================================
print("\n[3/4] Подготовка функций...")

def create_entity(tx, text, label):
    """Создаёт узел сущности"""
    # Очищаем label от спецсимволов
    clean_label = label.replace(" ", "_").upper()
    # Экранируем кавычки
    safe_text = text.replace('"', '\\"')
    
    query = f"""
    MERGE (n:{clean_label} {{name: $text}})
    RETURN n
    """
    tx.run(query, text=text)

def create_relationship(tx, from_text, to_text, rel_type):
    """Создаёт связь между двумя узлами"""
    query = f"""
    MATCH (a), (b)
    WHERE a.name = $from_text AND b.name = $to_text
    MERGE (a)-[r:{rel_type}]->(b)
    RETURN r
    """
    tx.run(query, from_text=from_text, to_text=to_text)

# ============================================================
# 4. Загрузка сущностей
# ============================================================
print("\n[4/4] Загрузка сущностей в Neo4j...")

nodes_created = 0
errors = 0

with driver.session() as session:
    for i, ent in enumerate(entities):
        try:
            session.execute_write(create_entity, ent["text"], ent["label"])
            nodes_created += 1
            
            if (i + 1) % 10 == 0:
                print(f"  Загружено {i + 1}/{len(entities)}...")
        except Exception as e:
            errors += 1
            if errors <= 5:  # Показываем только первые 5 ошибок
                print(f"  ⚠️  Ошибка с '{ent['text']}': {str(e)[:100]}")

print(f"\n   ✅ Загружено {nodes_created} узлов")
if errors > 0:
    print(f"   ⚠️  Ошибок: {errors}")

# ============================================================
# 5. Создание связей между сущностями
# ============================================================
print("\n🔗 Создание связей между сущностями...")

relationships_created = 0
relationship_types = {}

with driver.session() as session:
    for i in range(len(entities) - 1):
        ent1 = entities[i]
        ent2 = entities[i + 1]
        
        label1 = ent1["label"]
        label2 = ent2["label"]
        
        # Определяем тип связи на основе типов сущностей
        rel_type = None
        
        # Материал используется в процессе
        if label1 in ["MATERIAL", "ALLOY"] and label2 in ["PROCESS", "TEMPERATURE"]:
            rel_type = "USED_IN"
        
        # Процесс требует оборудование
        elif label1 in ["PROCESS"] and label2 in ["EQUIPMENT"]:
            rel_type = "REQUIRES"
        
        # Процесс влияет на свойство
        elif label1 in ["PROCESS"] and label2 in ["PROPERTY", "PROPERTY_VALUE"]:
            rel_type = "AFFECTS"
        
        # Температура приводит к значению свойства
        elif label1 in ["TEMPERATURE"] and label2 in ["PROPERTY_VALUE"]:
            rel_type = "RESULTS_IN"
        
        # Организация связана с человеком
        elif label1 in ["ORG"] and label2 in ["PER"]:
            rel_type = "EMPLOYS"
        
        # Локация связана с организацией
        elif label1 in ["LOC"] and label2 in ["ORG"]:
            rel_type = "CONTAINS"
        
        if rel_type:
            try:
                session.execute_write(
                    create_relationship,
                    ent1["text"],
                    ent2["text"],
                    rel_type
                )
                relationships_created += 1
                
                # Считаем типы связей
                if rel_type not in relationship_types:
                    relationship_types[rel_type] = 0
                relationship_types[rel_type] += 1
                
            except Exception as e:
                pass  # Игнорируем ошибки при создании связей

print(f"   ✅ Создано {relationships_created} связей")

if relationship_types:
    print("\n   Типы связей:")
    for rel_type, count in sorted(relationship_types.items()):
        print(f"     {rel_type}: {count}")

# ============================================================
# 6. Завершение
# ============================================================
driver.close()

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print(f"\n📊 Статистика:")
print(f"   Узлов создано: {nodes_created}")
print(f"   Связей создано: {relationships_created}")
print(f"\n📊 Теперь откройте Neo4j Browser (http://localhost:7474)")
print("   и выполните запросы:")
print("\n   // Посмотреть все узлы:")
print("   MATCH (n) RETURN n LIMIT 50")
print("\n   // Посмотреть связи:")
print("   MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 20")
print("\n   // Посчитать узлы по типам:")
print("   MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
print("   ORDER BY count DESC")