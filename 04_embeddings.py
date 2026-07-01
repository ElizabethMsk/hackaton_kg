from sentence_transformers import SentenceTransformer
import chromadb
import json

print("Загрузка модели эмбеддингов...")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("✅ Модель загружена!")

# Читаем текст статьи
print("\nЧтение text.json...")
with open("text.json", "r", encoding="utf-8") as f:
    data = json.load(f)
text = data["text"]

# Разбиваем на абзацы (по маркерам страниц)
print("Разбиение текста на абзацы...")
paragraphs = text.split("--- Страница")
paragraphs = [p.strip() for p in paragraphs if p.strip()]

print(f"Найдено абзацев: {len(paragraphs)}")

# Создаём эмбеддинги для каждого абзаца
print("\nСоздание эмбеддингов (может занять 1-2 минуты)...")
embeddings = model.encode(paragraphs, show_progress_bar=True)

print(f"✅ Создано {len(embeddings)} векторов размером {len(embeddings[0])}")

# Сохраняем в ChromaDB
print("\nСохранение в ChromaDB...")
client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_or_create_collection(
    name="articles",
    metadata={"hnsw:space": "cosine"}
)

# Добавляем в коллекцию
collection.add(
    ids=[f"para_{i}" for i in range(len(paragraphs))],
    embeddings=embeddings.tolist(),
    documents=paragraphs,
    metadatas=[{"page": i+1} for i in range(len(paragraphs))]
)

print(f"✅ Сохранено {len(paragraphs)} абзацев в ChromaDB")
print(f"📁 База данных сохранена в папке: ./vector_db")

# Тестовый поиск
print("\n" + "="*60)
print("ТЕСТОВЫЙ ПОИСК")
print("="*60)

query = "термообработка сплавов"
print(f"\nЗапрос: '{query}'")

query_embedding = model.encode([query])[0]
results = collection.query(
    query_embeddings=[query_embedding.tolist()],
    n_results=3,
    include=["documents", "metadatas", "distances"]
)

print(f"\nНайдено {len(results['documents'][0])} результатов:")
for i, (doc, dist, meta) in enumerate(zip(
    results['documents'][0], 
    results['distances'][0],
    results['metadatas'][0]
), 1):
    similarity = 1 - dist
    print(f"\n{i}. Страница {meta['page']} (похожесть: {similarity:.2%})")
    print(f"   {doc[:150]}...")