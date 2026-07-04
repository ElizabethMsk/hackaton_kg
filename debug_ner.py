from ml.mining_ner import MiningNER
from ml.custom_ner import MaterialNER
import json

# Загружаем тестовые данные
with open('metrics/test_data.json', 'r', encoding='utf-8') as f:
    test_data = json.load(f)

material_ner = MaterialNER()
mining_ner = MiningNER()

print('=' * 70)
print('ЧТО ИЗВЛЕКАЮТ МОДЕЛИ vs GROUND TRUTH')
print('=' * 70)

for test_case in test_data['test_cases'][:1]:  # Первый тест
    print(f'\nТекст: {test_case["text"][:100]}...\n')
    
    print('Ground Truth:')
    for ent in test_case['entities']:
        print(f'  [{ent["label"]:20}] {ent["text"]}')
    
    print('\nMaterialNER:')
    material_ents = material_ner.extract(test_case['text'])
    for ent in material_ents:
        print(f'  [{ent["label"]:20}] {ent["text"]} ({ent.get("source", "unknown")})')
    
    print('\nMiningNER:')
    mining_ents = mining_ner.extract(test_case['text'])
    for ent in mining_ents:
        print(f'  [{ent["label"]:20}] {ent["text"]} ({ent.get("source", "unknown")})')