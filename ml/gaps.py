from collections import defaultdict
from typing import List, Dict, Set

class GapAnalyzer:
    def __init__(self):
        self.all_materials: Set[str] = set()
        self.all_properties: Set[str] = set()
        self.all_regimes: Set[str] = set()
        self.material_properties: Dict[str, Set[str]] = defaultdict(set)
        self.material_regimes: Dict[str, Set[str]] = defaultdict(set)
        self.experiment_results: Dict[tuple, List] = defaultdict(list)
    
    def add_experiment(self, material: str, regime: str, 
                       property_name: str, value: float):
        """Добавляет данные эксперимента"""
        self.all_materials.add(material)
        self.all_properties.add(property_name)
        self.all_regimes.add(regime)
        
        self.material_properties[material].add(property_name)
        self.material_regimes[material].add(regime)
        self.experiment_results[(material, regime)].append({
            "property": property_name,
            "value": value
        })
    
    def find_coverage_gaps(self) -> List[Dict]:
        """Пары (материал, свойство), которые не изучались"""
        gaps = []
        for material in self.all_materials:
            studied = self.material_properties[material]
            unstudied = self.all_properties - studied
            for prop in unstudied:
                gaps.append({
                    "type": "coverage",
                    "material": material,
                    "property": prop,
                    "description": f"{material} — не изучено '{prop}'"
                })
        return gaps
    
    def find_regime_gaps(self, min_regimes: int = 3) -> List[Dict]:
        """Материалы, изученные при малом числе режимов"""
        gaps = []
        for material in self.all_materials:
            regimes = self.material_regimes[material]
            if len(regimes) < min_regimes:
                gaps.append({
                    "type": "regime",
                    "material": material,
                    "studied_regimes": len(regimes),
                    "description": f"{material} изучен только при {len(regimes)} режимах"
                })
        return sorted(gaps, key=lambda x: x["studied_regimes"])
    
    def find_contradictions(self, threshold: float = 0.15) -> List[Dict]:
        """Противоречия: одинаковые условия → разные результаты"""
        contradictions = []
        for (material, regime), results in self.experiment_results.items():
            if len(results) < 2:
                continue
            
            by_property = defaultdict(list)
            for r in results:
                by_property[r["property"]].append(r["value"])
            
            for prop, values in by_property.items():
                if len(values) < 2:
                    continue
                avg = sum(values) / len(values)
                if avg == 0:
                    continue
                spread = (max(values) - min(values)) / avg
                if spread > threshold:
                    contradictions.append({
                        "type": "contradiction",
                        "material": material,
                        "regime": regime,
                        "property": prop,
                        "values": values,
                        "spread": spread,
                        "description": f"{material} + {regime} → {prop}: разброс {spread:.1%}"
                    })
        return sorted(contradictions, key=lambda x: x["spread"], reverse=True)
    
    def get_summary(self) -> Dict:
        return {
            "total_materials": len(self.all_materials),
            "total_properties": len(self.all_properties),
            "total_regimes": len(self.all_regimes),
            "coverage_gaps": len(self.find_coverage_gaps()),
            "regime_gaps": len(self.find_regime_gaps()),
            "contradictions": len(self.find_contradictions())
        }


if __name__ == "__main__":
    analyzer = GapAnalyzer()
    
    # Тестовые данные
    analyzer.add_experiment("Сталь 45", "закалка 850°C", "твёрдость", 58)
    analyzer.add_experiment("Сталь 45", "закалка 850°C", "твёрдость", 42)
    analyzer.add_experiment("Сталь 45", "отпуск 200°C", "твёрдость", 55)
    analyzer.add_experiment("ВТ1-0", "закалка 900°C", "прочность", 800)
    
    print("=== Сводка ===")
    summary = analyzer.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\n=== Пробелы покрытия ===")
    for gap in analyzer.find_coverage_gaps()[:5]:
        print(f"  • {gap['description']}")
    
    print("\n=== Противоречия ===")
    for gap in analyzer.find_contradictions():
        print(f"  ⚠️  {gap['description']}")