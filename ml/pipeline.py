"""
ML Pipeline — связывает все модули вместе
"""
try:
    from .mining_ner import MiningNER
except ImportError:
    from .custom_ner import MaterialNER as MiningNER
from .chunker import TextChunker
from .ranking import ResultRanker
from .gaps import GapAnalyzer

class MLPipeline:
    """Основной пайплайн обработки документов"""
    
    def __init__(self):
        try:
             from .mining_ner import MiningNER
        except ImportError:
             from .custom_ner import MaterialNER as MiningNER
         
        self.ner = MiningNER()
        self.chunker = TextChunker()
        self.ranker = ResultRanker()
        self.gap_analyzer = GapAnalyzer()
    
    def process_document(self, text: str) -> dict:
        """Обрабатывает документ: извлекает сущности и разбивает на чанки"""
        
        # 1. Извлечение сущностей
        entities = self.ner.extract(text)
        
        # 2. Разбиение на чанки
        chunks = self.chunker.chunk(text)
        
        # 3. Извлечение всех уникальных сущностей по типам
        materials = set()
        temperatures = set()
        properties = set()
        
        for ent in entities:
            if ent["label"] == "ALLOY":
                materials.add(ent["text"])
            elif ent["label"] == "TEMPERATURE":
                temperatures.add(ent["text"])
            elif ent["label"] in ["PROPERTY", "PROPERTY_VALUE"]:
                properties.add(ent["text"])
        
        return {
            "entities": entities,
            "chunks": chunks,
            "materials": list(materials),
            "temperatures": list(temperatures),
            "properties": list(properties)
        }
    
    def analyze_gaps(self, materials: list, properties: list, experiments: list):
        """Анализирует пробелы в данных"""
        # Добавляем эксперименты в анализатор
        for exp in experiments:
            self.gap_analyzer.add_experiment(
                exp["material"],
                exp["regime"],
                exp["property"],
                exp["value"]
            )
        
        return self.gap_analyzer.get_summary()
    
    def rank_results(self, query: str, results: list, query_entities: list = None):
        """Ранжирует результаты поиска"""
        return self.ranker.rank(query, results, query_entities)


if __name__ == "__main__":
    # Тест пайплайна
    pipeline = MLPipeline()
    
    test_text = """
    Сталь 45 подвергалась закалке при температуре 850°C.
    Время выдержки составляло 2 часа.
    После закалки твёрдость достигла 58 HRC.
    
    Отпуск проводился при 200°C в течение 1 часа.
    Итоговая твёрдость после отпуска — 55 HRC.
    """
    
    print("=" * 60)
    print("ТЕСТ ML PIPELINE")
    print("=" * 60)
    
    result = pipeline.process_document(test_text)
    
    print(f"\nНайдено сущностей: {len(result['entities'])}")
    print(f"Создано чанков: {len(result['chunks'])}")
    print(f"\nМатериалы: {result['materials']}")
    print(f"Температуры: {result['temperatures']}")
    print(f"Свойства: {result['properties']}")
    
    # Тест анализа пробелов
    print("\n" + "=" * 60)
    print("ТЕСТ АНАЛИЗА ПРОБЕЛОВ")
    print("=" * 60)
    
    experiments = [
        {"material": "Сталь 45", "regime": "закалка 850°C", "property": "твёрдость", "value": 58},
        {"material": "Сталь 45", "regime": "закалка 850°C", "property": "твёрдость", "value": 42},
        {"material": "Сталь 45", "regime": "отпуск 200°C", "property": "твёрдость", "value": 55},
        {"material": "ВТ1-0", "regime": "закалка 900°C", "property": "прочность", "value": 800},
    ]
    
    summary = pipeline.analyze_gaps(result['materials'], result['properties'], experiments)
    
    print(f"\nВсего материалов: {summary['total_materials']}")
    print(f"Всего свойств: {summary['total_properties']}")
    print(f"Пробелов покрытия: {summary['coverage_gaps']}")
    print(f"Противоречий: {summary['contradictions']}")
    
    print("\n Pipeline работает!")
    