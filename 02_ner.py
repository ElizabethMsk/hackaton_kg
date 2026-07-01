import spacy
import json
from collections import Counter

print("Загрузка модели spaCy...")
nlp = spacy.load("ru_core_news_lg")
print("✅ Модель загружена!")

# Читаем извлечённый текст
print("\nЧтение text.json...")
with open("text.json", "r", encoding="utf-8") as f:
    data = json.load(f)
text = data["text"]

print("Обработка текста (может занять 1-2 минуты)...")
doc = nlp(text)

# Собираем все сущности
entities = []
for ent in doc.ents:
    entities.append({
        "text": ent.text,
        "label": ent.label_,
        "start": ent.start_char,
        "end": ent.end_char
    })

# Сохраняем в JSON
with open("entities.json", "w", encoding="utf-8") as f:
    json.dump(entities, f, ensure_ascii=False, indent=2)

# Статистика
print(f"\n✅ Найдено сущностей: {len(entities)}")

labels = Counter(e["label"] for e in entities)
print("\nПо типам:")
for label, count in labels.most_common():
    print(f"  {label}: {count}")

print("\nПримеры найденных сущностей:")
for i, e in enumerate(entities[:15]):
    print(f"  [{e['label']:10}] {e['text']}")