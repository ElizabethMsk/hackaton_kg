import spacy
import re
from typing import List, Dict

class MiningNER:
    """NER для горно-металлургической отрасли"""
    
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_lg")
        
        # Словарь синонимов
        self.synonyms = {
            "электроэкстракция": ["electrowinning", "электрорафинирование"],
            "ПВП": ["печь взвешенной плавки", "fluidized bed furnace", "FBF"],
            "выщелачивание": ["leaching", "кучное выщелачивание", "heap leaching"],
            "штейн": ["matte", "медный штейн", "никелевый штейн"],
            "шлак": ["slag", "печной шлак"],
        }
    
    def extract(self, text: str) -> List[Dict]:
        entities = []
        doc = self.nlp(text)
        
        # 1. Стандартные сущности spaCy
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "source": "spacy"
            })
        
        # 2. Материалы (металлы, соединения)
        materials = [
            r"(?:никель|Ni|медь|Cu|кобальт|Co|золото|Au|серебро|Ag|МПГ|платина|Pt|палладий|Pd)",
            r"(?:сульфат[ы]?|хлорид[ы]?|гипс|техногенный\s+гипс|угольные\s+отходы)",
            r"(?:штейн|шлак|катод|анод|шихта|католит|электролит)",
        ]
        for pattern in materials:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "MATERIAL",
                    "source": "regex"
                })
        
        # 3. Процессы
        processes = [
            r"(?:выщелачивание|leaching|электроэкстракция|electrowinning|электролиз)",
            r"(?:плавка|обжиг|гидрометаллургия|пирометаллургия|аффинаж)",
            r"(?:очистка\s+(?:воды|газов|стоков)|обессоливание)",
            r"(?:кучное\s+выщелачивание|heap\s+leaching|ПВП)",
        ]
        for pattern in processes:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "PROCESS",
                    "source": "regex"
                })
        
        # 4. Оборудование
        equipment = [
            r"(?:ванна\s+электроэкстракции|диафрагменная\s+ячейка|электролизер)",
            r"(?:печь\s+взвешенной\s+плавки|ПВП|fluidized\s+bed\s+furnace)",
            r"(?:автолав|реактор|сгуститель|фильтр-пресс)",
        ]
        for pattern in equipment:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "EQUIPMENT",
                    "source": "regex"
                })
        
        # 5. Числовые ограничения (КРИТИЧНО для ТЗ!)
        # ≤300 мг/л, >=200°C, 100-500 т/сут, 200–300 мг/дм³
        numeric_patterns = [
            r"[≤<>=]+\s*\d+\.?\d*\s*(?:мг/л|мг/дм³|°C|т/сут|м³/ч|кПа|%)",
            r"\d+\.?\d*\s*[–-]\s*\d+\.?\d*\s*(?:мг/л|мг/дм³|°C|т/сут)",
            r"(?:от\s+)?\d+\.?\d*\s*(?:до|–|-)\s*\d+\.?\d*\s*(?:мг/л|°C|т/сут)",
        ]
        for pattern in numeric_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "label": "NUMERIC_CONSTRAINT",
                    "source": "regex"
                })
        
        # 6. География (отечественная/зарубежная практика)
        geo_patterns = [
            (r"(?:Россия|РФ|СССР|Сибирь|Урал|Норильск|Кольский)", "RU"),
            (r"(?:США|USA|Канада|Китай|China|Австралия|Чили|Казахстан)", "INTL"),
        ]
        for pattern, geo in geo_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "label": f"GEO_{geo}",
                    "source": "regex"
                })
        
        # 7. Нормализация синонимов
        entities = self._normalize_synonyms(entities)
        
        # Удаление дубликатов
        seen = set()
        unique = []
        for ent in entities:
            key = (ent["text"].lower(), ent["label"])
            if key not in seen:
                seen.add(key)
                unique.append(ent)
        
        return unique
    
    def _normalize_synonyms(self, entities: List[Dict]) -> List[Dict]:
        """Заменяет синонимы на канонические названия"""
        normalized = []
        for ent in entities:
            canonical = ent["text"]
            for canon, syns in self.synonyms.items():
                if ent["text"].lower() in [s.lower() for s in syns]:
                    canonical = canon
                    break
            normalized.append({
                **ent,
                "canonical": canonical
            })
        return normalized


if __name__ == "__main__":
    ner = MiningNER()
    
    test_text = """
    При электроэкстракции никеля скорость циркуляции католита 
    составляет 0.3-0.5 м/с. Концентрация сульфатов в воде 
    не должна превышать 300 мг/л, хлоридов — 200 мг/л.
    
    В мировой практике (США, Канада) применяется кучное 
    выщелачивание медных руд. В России (Норильск) используют 
    печи взвешенной плавки (ПВП) для переработки штейна.
    
    Распределение Au и Ag между медным штейном и шлаком 
    зависит от температуры плавки (1200-1300°C).
    """
    
    entities = ner.extract(test_text)
    
    print(f"Найдено {len(entities)} сущностей:\n")
    for ent in entities:
        canon = f" → {ent.get('canonical', '')}" if ent.get('canonical') != ent['text'] else ""
        print(f"  [{ent['label']:18}] {ent['text']:35}{canon}")