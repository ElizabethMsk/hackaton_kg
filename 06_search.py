from sentence_transformers import SentenceTransformer
import chromadb
import json

# Загружаем модель
print("Загрузка модели...")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Подключаемся к ChromaDB
client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_collection("articles")

print("\n" + "="*60)
print("ПОИСК ПО СТАТЬЯМ")
print("="*60)
print("Введите вопрос (или 'exit' для выхода)\n")

while True:
    query = input("❓ Вопрос: ").strip()
    
    if query.lower() in ['exit', 'quit', 'выход']:
        break
    
    if not query:
        continue
    
    # Ищем похожие абзацы
    query_embedding = model.encode([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=5,
        include=["documents", "metadatas", "distances"]
    )
    
    print(f"\n🔍 Найдено {len(results['documents'][0])} результатов:\n")
    
    for i, (doc, dist, meta) in enumerate(zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0]
    ), 1):
        similarity = 1 - dist
        print(f"{i}. Страница {meta['page']} (похожесть: {similarity:.2%})")
        print(f"   {doc[:200]}...")
        print()
    
    print("-" * 60)