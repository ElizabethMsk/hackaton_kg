import requests
import json
import sys
import os
from sentence_transformers import SentenceTransformer
import chromadb

print("=" * 60)
print("RAG ПОИСК С YANDEX GPT")
print("=" * 60)

# ============================================================
# 1. Загрузка конфигурации
# ============================================================
print("\n[1/4] Загрузка конфигурации...")

# Пробуем загрузить конфиг
config_path = os.path.join(os.path.dirname(__file__), 'config.py')
config = {}

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        exec(f.read(), config)
    
    YANDEX_GPT_API_KEY = config.get('YANDEX_GPT_API_KEY')
    YANDEX_GPT_FOLDER_ID = config.get('YANDEX_GPT_FOLDER_ID')
    
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        print("   ❌ Ошибка: Не найдены ключи Yandex GPT в config.py")
        print("   Добавьте в ml/config.py:")
        print("   YANDEX_GPT_API_KEY = 'ваш_ключ'")
        print("   YANDEX_GPT_FOLDER_ID = 'ваш_folder_id'")
        sys.exit(1)
    
    print("   ✅ Конфигурация загружена")
    print(f"   API Key: {YANDEX_GPT_API_KEY[:10]}...")
    print(f"   Folder ID: {YANDEX_GPT_FOLDER_ID}")
    
except Exception as e:
    print(f"   ❌ Ошибка загрузки конфига: {e}")
    sys.exit(1)

# ============================================================
# 2. Загрузка модели эмбеддингов
# ============================================================
print("\n[2/4] Загрузка модели эмбеддингов...")

try:
    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    print("   ✅ Модель загружена!")
except Exception as e:
    print(f"   ❌ Ошибка загрузки модели: {e}")
    sys.exit(1)

# ============================================================
# 3. Подключение к ChromaDB
# ============================================================
print("\n[3/4] Подключение к векторной базе...")

try:
    client = chromadb.PersistentClient(path="./vector_db")
    collection = client.get_collection("articles")
    print(f"   ✅ Подключено к базе: ./vector_db")
    print(f"   Всего документов: {collection.count()}")
except Exception as e:
    print(f"   ❌ Ошибка подключения к ChromaDB: {e}")
    print("   Сначала запустите: python 04_embeddings.py")
    sys.exit(1)

# ============================================================
# 4. Класс для работы с Yandex GPT
# ============================================================
print("\n[4/4] Инициализация Yandex GPT...")

class YandexGPTClient:
    def __init__(self, api_key, folder_id):
        self.api_key = api_key
        self.folder_id = folder_id
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    def generate_answer(self, query, context):
        """Генерирует ответ на вопрос с использованием контекста"""
        
        prompt = f"""Ты — эксперт-металлург и научный консультант в горно-металлургической отрасли.

Твоя задача: ответить на вопрос пользователя, используя ТОЛЬКО предоставленный контекст из научных статей и технических отчётов.

ПРАВИЛА:
1. Если в контексте нет точного ответа, скажи: "В доступных источниках не найдено информации по этому вопросу"
2. Используй конкретные цифры, параметры и технические детали из контекста
3. Указывай источники (номера страниц), если они есть
4. Отвечай подробно, но по делу
5. Используй профессиональную терминологию

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

КОНТЕКСТ ИЗ ДОКУМЕНТОВ:
{context}

ОТВЕТ:"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}"
        }
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 1500
            },
            "messages": [
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            answer = result["result"]["alternatives"][0]["message"]["text"]
            return answer.strip()
            
        except requests.exceptions.Timeout:
            return "⏱️  Превышено время ожидания ответа от Yandex GPT. Попробуйте ещё раз."
        except Exception as e:
            return f"❌ Ошибка при обращении к Yandex GPT: {str(e)[:200]}"

# Инициализация клиента
gpt_client = YandexGPTClient(YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID)
print("   ✅ Yandex GPT готов к работе!")

# ============================================================
# 5. Функция поиска и генерации ответа
# ============================================================
def search_and_answer(query, n_results=3):
    """
    Поиск релевантных документов и генерация ответа
    
    Args:
        query: вопрос пользователя
        n_results: количество найденных документов
    
    Returns:
        dict с ответом и источниками
    """
    print(f"\n🔍 Поиск в базе знаний...")
    
    # 1. Создаём эмбеддинг запроса
    query_embedding = model.encode([query])[0]
    
    # 2. Ищем похожие документы
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    # 3. Формируем контекст
    context_parts = []
    sources = []
    
    for i, (doc, dist, meta) in enumerate(zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0]
    ), 1):
        similarity = 1 - dist
        page = meta.get('page', '?')
        
        context_parts.append(f"[Источник {i}, стр. {page}]\n{doc}")
        
        sources.append({
            "index": i,
            "page": page,
            "similarity": similarity,
            "text": doc[:200] + "..." if len(doc) > 200 else doc
        })
    
    context = "\n\n".join(context_parts)
    
    # 4. Генерируем ответ через GPT
    print(f"🤖 Генерация ответа через Yandex GPT...")
    answer = gpt_client.generate_answer(query, context)
    
    return {
        "answer": answer,
        "sources": sources,
        "context": context
    }

# ============================================================
# 6. Интерактивный режим
# ============================================================
print("\n" + "=" * 60)
print("ГОТОВО! Задавайте вопросы")
print("=" * 60)
print("\nПримеры вопросов из ТЗ хакатона:")
print("  1. Какие методы обессоливания воды подходят для обогатительной фабрики?")
print("  2. Какая оптимальная скорость циркуляции католита при электроэкстракции?")
print("  3. Что известно о распределении золота и серебра между штейном и шлаком?")
print("  4. Какие технические решения подачи электролита существуют?")
print("\nВведите 'exit' для выхода")
print("-" * 60)

# Тестовые вопросы для демонстрации
test_queries = [
    "Какие методы обессоливания воды подходят при сульфатах до 300 мг/л?",
    "Какая скорость циркуляции католита оптимальна?",
    "Как распределяются драгоценные металлы между штейном и шлаком?"
]

# Спрашиваем, хочет ли пользователь тестовый режим
mode = input("\nВыберите режим:\n  [1] Тестовый (3 вопроса из ТЗ)\n  [2] Интерактивный (свой вопрос)\nВаш выбор: ").strip()

if mode == "1":
    # Тестовый режим
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"ВОПРОС {i}: {query}")
        print('='*60)
        
        result = search_and_answer(query, n_results=3)
        
        print("\n💡 ОТВЕТ СИСТЕМЫ:")
        print("-" * 60)
        print(result["answer"])
        
        print("\n📚 ИСТОЧНИКИ:")
        print("-" * 60)
        for source in result["sources"]:
            print(f"\n[{source['index']}] Страница {source['page']} (похожесть: {source['similarity']:.2%})")
            print(f"    {source['text']}")
        
        if i < len(test_queries):
            input("\nНажмите Enter для следующего вопроса...")
    
    print("\n" + "=" * 60)
    print("✅ Тестовый режим завершён!")
    print("=" * 60)

else:
    # Интерактивный режим
    while True:
        try:
            query = input("\n❓ Ваш вопрос: ").strip()
            
            if query.lower() in ['exit', 'quit', 'выход', 'q']:
                print("\n👋 До свидания!")
                break
            
            if not query:
                continue
            
            result = search_and_answer(query, n_results=3)
            
            print("\n" + "=" * 60)
            print("💡 ОТВЕТ:")
            print("=" * 60)
            print(result["answer"])
            
            print("\n" + "=" * 60)
            print("📚 ИСТОЧНИКИ:")
            print("=" * 60)
            for source in result["sources"]:
                print(f"\n[{source['index']}] Страница {source['page']} (похожесть: {source['similarity']:.2%})")
                print(f"    {source['text']}")
            
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            print("Попробуйте ещё раз")

print("\nСпасибо за использование RAG поиска!")