from neo4j import GraphDatabase
import json

print("Подключение к Neo4j...")
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test1234"))

print("Чтение entities.json...")
with open("entities.json", "r", encoding="utf-8") as f:
    entities = json.load(f)

# Функция для создания узла
def create_entity(tx, text, label):
    # Очищаем label от спецсимволов (Neo4j не любит пробелы в названиях меток)
    clean_label = label.replace(" ", "_").upper()
    
    # Экранируем кавычки в тексте
    safe_text = text.replace('"', '\\"')
    
    query = f"""
    MERGE (n:{clean_label} {{name: $text}})
    RETURN n
    """
    tx.run(query, text=text)

print(f"Загрузка {len(entities)} сущностей в Neo4j...")

# Загружаем все сущности
with driver.session() as session:
    for i, ent in enumerate(entities):
        try:
            session.execute_write(create_entity, ent["text"], ent["label"])
            if (i + 1) % 10 == 0:
                print(f"  Загружено {i + 1}/{len(entities)}...")
        except Exception as e:
            print(f"  ⚠️  Ошибка с '{ent['text']}': {e}")

driver.close()

print(f"\n✅ Готово! Загружено {len(entities)} сущностей в Neo4j")
print("\nТеперь откройте Neo4j Browser (http://localhost:7474) и выполните:")
print("MATCH (n) RETURN n LIMIT 50")