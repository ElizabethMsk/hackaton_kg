"""
Модуль для оценки качества NER
"""
from typing import List, Dict, Set, Tuple
from collections import defaultdict

class NEREvaluator:
    """Оценка качества извлечения сущностей"""
    
    def __init__(self, ground_truth: List[Dict]):
        self.ground_truth = ground_truth
    
    def _entities_to_set(self, entities: List[Dict]) -> Set[Tuple]:
        """Преобразует сущности в множество кортежей (text_lower, label)"""
        return set((e["text"].lower().strip(), e["label"].upper().strip()) for e in entities)
    
    def precision(self, predicted: List[Dict]) -> float:
        """Точность: сколько извлечённых сущностей правильные"""
        pred_set = self._entities_to_set(predicted)
        true_set = self._entities_to_set(self.ground_truth)
        
        if not pred_set:
            return 0.0
        
        correct = len(pred_set & true_set)
        return correct / len(pred_set)
    
    def recall(self, predicted: List[Dict]) -> float:
        """Полнота: сколько правильных сущностей найдено"""
        pred_set = self._entities_to_set(predicted)
        true_set = self._entities_to_set(self.ground_truth)
        
        if not true_set:
            return 0.0
        
        correct = len(pred_set & true_set)
        return correct / len(true_set)
    
    def f1_score(self, predicted: List[Dict]) -> float:
        """F1-score"""
        p = self.precision(predicted)
        r = self.recall(predicted)
        
        if p + r == 0:
            return 0.0
        
        return 2 * (p * r) / (p + r)
    
    def detailed_report(self, predicted: List[Dict]) -> str:
        """Развёрнутый отчёт"""
        lines = []
        lines.append("=" * 70)
        lines.append("ОТЧЁТ О КАЧЕСТВЕ NER")
        lines.append("=" * 70)
        
        p = self.precision(predicted)
        r = self.recall(predicted)
        f1 = self.f1_score(predicted)
        
        lines.append(f"\nОБЩИЕ МЕТРИКИ:")
        lines.append(f"  Precision: {p:.2%}")
        lines.append(f"  Recall:    {r:.2%}")
        lines.append(f"  F1-Score:  {f1:.2%}")
        
        # Примеры ошибок
        pred_set = self._entities_to_set(predicted)
        true_set = self._entities_to_set(self.ground_truth)
        
        false_positives = pred_set - true_set
        false_negatives = true_set - pred_set
        
        if false_positives:
            lines.append(f"\n  Ложные срабатывания (False Positives):")
            for text, label in list(false_positives)[:5]:
                lines.append(f"    - {text} ({label})")
        
        if false_negatives:
            lines.append(f"\n  Пропущенные сущности (False Negatives):")
            for text, label in list(false_negatives)[:5]:
                lines.append(f"    - {text} ({label})")
        
        return "\n".join(lines)