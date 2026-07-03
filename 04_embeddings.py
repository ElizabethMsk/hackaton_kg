from sentence_transformers import SentenceTransformer
import chromadb
import json
import sys
import os

# Добавляем путь к ml-модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("СОЗДАНИЕ ЭМБЕДДИНГОВ С МЕТАДАННЫМИ")
print("=" * 60)

# ============================================================
# 1. Загрузка модели эмбеддингов
# ============================================================
print("\n[1/5] Загрузка модели эмбеддингов...")
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
print("Модель загружена!")

# ============================================================
# 2. Загрузка NER для извлечения метаданных
# ============================================================
print("\n[2/5] Загрузка NER для метаданных...")
try:
    from ml.mining_ner import MiningNER
    ner = MiningNER()
    print("MiningNER загружен (горно-металлургический)")
except ImportError:
    try:
        from ml.custom_ner import MaterialNER
        ner = MaterialNER()
        print("MaterialNER загружен (fallback)")
    except ImportError:
        import spacy
        ner = spacy.load("ru_core_news_lg")
        print("Используется базовый spaCy (без правил)")

# ============================================================
# 3. Чтение текста
# ============================================================
print("\n[3/5] Чтение text.json...")
with open("text.json", "r", encoding="utf-8") as f:
    data = json.load(f)
text = data["text"]

# Разбиваем на абзацы (по маркерам страниц)
print("Разбиение текста на абзацы...")
paragraphs = text.split("--- Страница")
paragraphs = [p.strip() for p in paragraphs if p.strip()]
print(f"Найдено абзацев: {len(paragraphs)}")

# ============================================================
# 4. Создание эмбеддингов
# ============================================================
print("\n[4/5] Создание эмбеддингов (может занять 1-2 минуты)...")
embeddings = model.encode(paragraphs, show_progress_bar=True)
print(f"Создано {len(embeddings)} векторов размером {len(embeddings[0])}")

# ============================================================
# 5. Извлечение метаданных для каждого абзаца
# ============================================================
print("\n[5/5] Извлечение метаданных из абзацев...")
metadatas = []
total_entities = 0

for i, paragraph in enumerate(paragraphs):
    meta = {
        "page": i + 1,
        "chunk_index": i,
        "length": len(paragraph)
    }
    
    # Извлекаем сущности из абзаца
    if hasattr(ner, 'extract'):
        entities = ner.extract(paragraph)
    else:
        # Fallback для обычного spaCy
        doc = ner(paragraph)
        entities = [
            {"text": ent.text, "label": ent.label_}
            for ent in doc.ents
        ]
    
    # Группируем сущности по типам
    materials = []
    processes = []
    equipment = []
    numeric = []
    geo_ru = []
    geo_intl = []
    
    for ent in entities:
        label = ent.get("label", ent.get("category", "UNKNOWN"))
        text = ent.get("text", "")
        
        if label == "MATERIAL":
            materials.append(text)
        elif label == "PROCESS":
            processes.append(text)
        elif label == "EQUIPMENT":
            equipment.append(text)
        elif label == "NUMERIC_CONSTRAINT":
            numeric.append(text)
        elif label == "GEO_RU":
            geo_ru.append(text)
        elif label == "GEO_INTL":
            geo_intl.append(text)
    
    # Сохраняем в метаданные (ChromaDB требует строки/числа)
    meta["materials"] = ", ".join(materials[:5]) if materials else ""
    meta["processes"] = ", ".join(processes[:3]) if processes else ""
    meta["equipment"] = ", ".join(equipment[:3]) if equipment else ""
    meta["numeric_constraints"] = ", ".join(numeric[:3]) if numeric else ""
    meta["has_numeric"] = len(numeric) > 0
    meta["geography_ru"] = ", ".join(geo_ru) if geo_ru else ""
    meta["geography_intl"] = ", ".join(geo_intl) if geo_intl else ""
    meta["entity_count"] = len(entities)
    
    metadatas.append(meta)
    total_entities += len(entities)

print(f"Извлечено {total_entities} сущностей из {len(paragraphs)} абзацев")

# Статистика по метаданным
abs_with_materials = sum(1 for m in metadatas if m["materials"])
abs_with_processes = sum(1 for m in metadatas if m["processes"])
abs_with_numeric = sum(1 for m in metadatas if m["has_numeric"])
abs_with_geo = sum(1 for m in metadatas if m["geography_ru"] or m["geography_intl"])

print(f"\n Статистика метаданных:")
print(f"   Абзацы с материалами: {abs_with_materials}/{len(paragraphs)}")
print(f"   Абзацы с процессами: {abs_with_processes}/{len(paragraphs)}")
print(f"   Абзацы с числовыми ограничениями: {abs_with_numeric}/{len(paragraphs)}")
print(f"   Абзацы с географией: {abs_with_geo}/{len(paragraphs)}")

# ============================================================
# 6. Сохранение в ChromaDB
# ============================================================
print("\nСохранение в ChromaDB...")
client = chromadb.PersistentClient(path="./vector_db")

# Удаляем старую коллекцию, если она есть (чтобы обновить метаданные)
try:
    client.delete_collection("articles")
    print("Удалена старая коллекция 'articles'")
except Exception:
    pass

collection = client.get_or_create_collection(
    name="articles",
    metadata={"hnsw:space": "cosine"}
)

# Добавляем в коллекцию
collection.add(
    ids=[f"para_{i}" for i in range(len(paragraphs))],
    embeddings=embeddings.tolist(),
    documents=paragraphs,
    metadatas=metadatas
)

print(f"Сохранено {len(paragraphs)} абзацев в ChromaDB")
print(f"База данных: ./vector_db")

# ============================================================
# 7. Тестовый поиск с демонстрацией метаданных
# ============================================================
print("\n" + "=" * 60)
print("ТЕСТОВЫЙ ПОИСК С МЕТАДАННЫМИ")
print("=" * 60)

test_queries = [
    "термообработка сплавов",
    "обессоливание воды сульфаты",
    "электроэкстракция никеля скорость католита",
    "кучное выщелачивание в России"
]

for query in test_queries:
    print(f"\nЗапрос: '{query}'")
    
    query_embedding = model.encode([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=2,
        include=["documents", "metadatas", "distances"]
    )
    
    print(f"   Найдено {len(results['documents'][0])} результатов:")
    for i, (doc, dist, meta) in enumerate(zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0]
    ), 1):
        similarity = 1 - dist
        print(f"\n   {i}. Страница {meta.get('page', '?')} (похожесть: {similarity:.2%})")
        
        # Показываем метаданные
        if meta.get("materials"):
            print(f"Материалы: {meta['materials']}")
        if meta.get("processes"):
            print(f"Процессы: {meta['processes']}")
        if meta.get("numeric_constraints"):
            print(f"       Ограничения: {meta['numeric_constraints']}")
        if meta.get("geography_ru"):
            print(f"Россия: {meta['geography_ru']}")
        if meta.get("geography_intl"):
            print(f"Мир: {meta['geography_intl']}")
        
        print(f"      {doc[:100]}...")

print("\n" + "=" * 60)
print("ГОТОВО! Эмбеддинги с метаданными созданы.")
print("=" * 60)