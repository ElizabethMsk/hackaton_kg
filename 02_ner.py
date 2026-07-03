import spacy
import json
from collections import Counter
import sys
sys.path.append('.')

# Используем улучшенный NER
try:
    from ml.mining_ner import MiningNER
    ner = MiningNER()
    print("Загрузка MiningNER...")
    print("Модель загружена!")
except ImportError:
    # Fallback на обычный spaCy
    from ml.custom_ner import MaterialNER
    ner = MaterialNER()
    print("Загрузка spaCy...")
    nlp = spacy.load("ru_core_news_lg")
    print("Модель загружена!")

print("\nЧтение text.json...")
with open("text.json", "r", encoding="utf-8") as f:
    data = json.load(f)
text = data["text"]

print("Обработка текста (может занять 1-2 минуты)...")

# Используем правильный NER
if hasattr(ner, 'extract'):
    entities = ner.extract(text)
else:
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        })

# Сохранение
with open("entities.json", "w", encoding="utf-8") as f:
    json.dump(entities, f, ensure_ascii=False, indent=2)

# Статистика
print(f"\nНайдено сущностей: {len(entities)}")
labels = Counter(e["label"] for e in entities)
print("\nПо типам:")
for label, count in labels.most_common():
    print(f"  {label}: {count}")

print("\nПримеры найденных сущностей:")
for i, e in enumerate(entities[:15]):
    print(f"  [{e['label']:18}] {e['text']}")