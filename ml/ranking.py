from typing import List, Dict

class ResultRanker:
    def __init__(self):
        self.weights = {
            "semantic": 0.40,
            "coverage": 0.25,
            "freshness": 0.15,
            "source": 0.10,
            "length": 0.10
        }
    
    def rank(self, query: str, results: List[Dict], 
             query_entities: List[str] = None) -> List[Dict]:
        """Ранжирует результаты поиска"""
        ranked = []
        
        for result in results:
            scores = {}
            
            # 1. Семантическая близость
            scores["semantic"] = 1.0 - result.get("distance", 1.0)
            
            # 2. Покрытие сущностями
            if query_entities:
                doc_entities = result.get("entities", [])
                overlap = len(set(doc_entities) & set(query_entities))
                scores["coverage"] = overlap / max(len(query_entities), 1)
            else:
                scores["coverage"] = 0.5
            
            # 3. Свежесть
            year = result.get("metadata", {}).get("year", 2020)
            scores["freshness"] = 1.0 / (1.0 + (2026 - year) * 0.1)
            
            # 4. Надёжность источника
            source_type = result.get("metadata", {}).get("source_type", "unknown")
            source_scores = {
                "peer_reviewed": 1.0,
                "internal_report": 0.7,
                "thesis": 0.5,
                "unknown": 0.3
            }
            scores["source"] = source_scores.get(source_type, 0.3)
            
            # 5. Длина фрагмента
            doc_length = len(result.get("document", ""))
            scores["length"] = min(doc_length / 1000.0, 1.0)
            
            # Итоговый score
            final_score = sum(
                self.weights[key] * scores[key] 
                for key in self.weights
            )
            
            ranked.append({
                **result,
                "score": final_score,
                "breakdown": scores
            })
        
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked
    
    def explain(self, result: Dict) -> str:
        """Объясняет ранжирование"""
        breakdown = result.get("breakdown", {})
        lines = [f"Итоговый score: {result['score']:.3f}\n"]
        
        for key, value in breakdown.items():
            weight = self.weights[key]
            contribution = weight * value
            lines.append(f"  {key:12}: {value:.2f} × {weight:.2f} = {contribution:.3f}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    ranker = ResultRanker()
    
    mock_results = [
        {
            "document": "Закалка стали 45 при 850°C даёт твёрдость 58 HRC",
            "distance": 0.15,
            "metadata": {"year": 2024, "source_type": "peer_reviewed"},
            "entities": ["Сталь 45", "закалка", "850°C"]
        },
        {
            "document": "Отпуск при 200°C",
            "distance": 0.45,
            "metadata": {"year": 2015, "source_type": "thesis"},
            "entities": ["отпуск"]
        }
    ]
    
    query_entities = ["Сталь 45", "закалка", "твёрдость"]
    ranked = ranker.rank("закалка стали 45", mock_results, query_entities)
    
    print("Ранжированные результаты:\n")
    for i, result in enumerate(ranked, 1):
        print(f"{i}. Score: {result['score']:.3f}")
        print(f"   Текст: {result['document'][:60]}...")
        print(ranker.explain(result))
        print()