"""
Сравнение методов извлечения сущностей
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics.evaluator import NEREvaluator
from ml.custom_ner import MaterialNER
from ml.mining_ner import MiningNER

print("=" * 70)
print("СРАВНЕНИЕ МЕТОДОВ ИЗВЛЕЧЕНИЯ СУЩНОСТЕЙ")
print("=" * 70)

# Загружаем тестовые данные
print("\n[1/4] Загрузка тестовых данных...")
with open("metrics/test_data.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

test_cases = test_data["test_cases"]
print(f"   Загружено {len(test_cases)} тестовых случаев")

# Инициализируем методы
print("\n[2/4] Инициализация методов...")
print("   Загрузка MaterialNER...")
material_ner = MaterialNER()

print("   Загрузка MiningNER...")
mining_ner = MiningNER()

# Тестирование
print("\n[3/4] Тестирование методов...")
results = {
    "MaterialNER": [],
    "MiningNER": []
}

for i, test_case in enumerate(test_cases, 1):
    print(f"\n   Тест {i}/{len(test_cases)}")
    
    ground_truth = test_case["entities"]
    
    # MaterialNER
    material_entities = material_ner.extract(test_case["text"])
    evaluator_material = NEREvaluator(ground_truth)
    results["MaterialNER"].append({
        "precision": evaluator_material.precision(material_entities),
        "recall": evaluator_material.recall(material_entities),
        "f1": evaluator_material.f1_score(material_entities)
    })
    
    # MiningNER
    mining_entities = mining_ner.extract(test_case["text"])
    evaluator_mining = NEREvaluator(ground_truth)
    results["MiningNER"].append({
        "precision": evaluator_mining.precision(mining_entities),
        "recall": evaluator_mining.recall(mining_entities),
        "f1": evaluator_mining.f1_score(mining_entities)
    })

# Агрегация результатов
print("\n[4/4] Агрегация результатов...")

print("\n" + "=" * 70)
print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
print("=" * 70)

for method_name, method_results in results.items():
    avg_precision = sum(r["precision"] for r in method_results) / len(method_results)
    avg_recall = sum(r["recall"] for r in method_results) / len(method_results)
    avg_f1 = sum(r["f1"] for r in method_results) / len(method_results)
    
    print(f"\n{method_name}:")
    print(f"  Precision: {avg_precision:.2%}")
    print(f"  Recall:    {avg_recall:.2%}")
    print(f"  F1-Score:  {avg_f1:.2%}")

# Определение победителя
best_method = max(results.keys(), 
                  key=lambda m: sum(r["f1"] for r in results[m]) / len(results[m]))

print("\n" + "=" * 70)
print(f" ПОБЕДИТЕЛЬ: {best_method}")
print("=" * 70)

# Сохранение результатов
output = {
    "summary": {
        "best_method": best_method,
        "results": {
            method: {
                "avg_precision": sum(r["precision"] for r in res) / len(res),
                "avg_recall": sum(r["recall"] for r in res) / len(res),
                "avg_f1": sum(r["f1"] for r in res) / len(res)
            }
            for method, res in results.items()
        }
    }
}

with open("metrics/results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n Результаты сохранены: metrics/results.json")