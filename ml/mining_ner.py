import spacy
import re
from typing import List, Dict

class MiningNER:
    """NER для горно-металлургической отрасли (максимально улучшенная версия)"""
    
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_lg")
        self.synonyms = {
            "электроэкстракция": ["electrowinning", "электрорафинирование"],
            "ПВП": ["печь взвешенной плавки", "печи взвешенной плавки", "fluidized bed furnace", "FBF"],
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
        
        # 2. Материалы (МАКСИМАЛЬНО ПОЛНЫЕ паттерны)
        materials = [
            # Металлы: все формы (им., род., дат., вин., твор., предл. + мн. число)
            r"\bникел[ьяюейе]\b",
            r"\bNi\b",
            r"\bмед[ьиюейе]\b",
            r"\bCu\b",
            r"\bкобальт[ауеовымымиах]\b",
            r"\bCo\b",
            r"\bзолот[ауеовымымиах]\b",
            r"\bAu\b",
            r"\bсеребр[ауеовымымиах]\b",
            r"\bAg\b",
            r"\bМПГ\b",
            r"\bплатин[аыуеовымымиах]\b",
            r"\bPt\b",
            r"\bпаллади[йяюеяемем]\b",
            r"\bPd\b",
            r"\bцинк[ауеовымымиах]\b",
            r"\bZn\b",
            r"\bжелез[ауеовымымиах]\b",
            r"\bFe\b",
            # Соединения: все падежи
            r"\bсульфат[аыуеовымымиах]*\b",
            r"\bхлорид[аыуеовымымиах]*\b",
            r"\bгипс[аыуеовымымиах]*\b",
            r"\bтехногенный\s+гипс\b",
            r"\bугольные?\s+отход[аыуеовымымиах]*\b",
            # Продукты металлургии
            r"\bштейн[аыуеовымымиах]*\b",
            r"\bшлак[аыуеовымымиах]*\b",
            r"\bкатод[аыуеовымымиах]*\b",
            r"\bанод[аыуеовымымиах]*\b",
            r"\bшихт[аыуеовымымиах]*\b",
            r"\bкатолит[аыуеовымымиах]*\b",
            r"\bэлектролит[аыуеовымымиах]*\b",
            # Руды и концентраты
            r"\bруд[аыуеовымымиах]*\b",
            r"\bконцентрат[аыуеовымымиах]*\b",
            # Прилагательные (медный, никелевый)
            r"\bмедн[аыуоейымымиых]\b",
            r"\bникелев[аыуоейымымиых]\b",
            r"\bкобальтов[аыуоейымымиых]\b",
            r"\bжелезн[аыуоейымымиых]\b",
            r"\bцинков[аыуоейымымиых]\b",
            # Составные материалы
            r"\bмедно-никелев[аыуоейымымиых]\b",
            r"\bникель-кобальтов[аыуоейымымиых]\b",
            r"\bжелезо-никелев[аыуоейымымиых]\b",
        ]
        for pattern in materials:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "MATERIAL",
                    "source": "regex"
                })
        
        # 3. Процессы (МАКСИМАЛЬНО ПОЛНЫЕ)
        processes = [
            # Основные процессы
            r"\bвыщелачивани[яиюеяемемях]\b",
            r"\bleaching\b",
            r"\bэлектроэкстракци[яиюеяемемях]\b",
            r"\belectrowinning\b",
            r"\bэлектролиз[ауеовымымиах]*\b",
            r"\bплавк[аиуеойымыхами]*\b",
            r"\bобжиг[аиуеойымыхами]*\b",
            r"\bгидрометаллурги[яиюеяемемях]\b",
            r"\bпирометаллурги[яиюеяемемях]\b",
            r"\bаффинаж[аиуеойымыхами]*\b",
            # Очистка и обработка
            r"\bочистк[аиуеойымыхами]*\s+(?:воды|газов|стоков|растворов)\b",
            r"\bобессоливани[яиюеяемемях]\b",
            r"\bкучное\s+выщелачивани[еяиюемях]\b",
            r"\bheap\s+leaching\b",
            r"\bПВП\b",
            # Дополнительные процессы
            r"\bрафинировани[яиюеяемемях]\b",
            r"\bконцентрировани[яиюеяемемях]\b",
            r"\bобогащени[яиюеяемемях]\b",
            r"\bпереработк[аиуеойымыхами]*\b",
            r"\bразделени[яиюеяемемях]\b",
            r"\bизвлечени[яиюеяемемях]\b",
            r"\bосаждени[яиюеяемемях]\b",
            r"\bэкстракци[яиюеяемемях]\b",
            r"\bсорбци[яиюеяемемях]\b",
            r"\bдистилляци[яиюеяемемях]\b",
            r"\bкристаллизаци[яиюеяемемях]\b",
        ]
        for pattern in processes:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "PROCESS",
                    "source": "regex"
                })
        
        # 4. Оборудование (МАКСИМАЛЬНО ПОЛНОЕ)
        equipment = [
            r"\bванн[аыуеойымыхами]*\s+электроэкстракци[иия]\b",
            r"\bдиафрагменн[аыуоейымыхыми]\s+ячейк[аиуеойымыхами]*\b",
            r"\bэлектролиз[её]р[аыуеовымымиах]*\b",
            r"\bпеч[ьиюеиойямьямиах]*\s+взвешенной\s+плавк[иия]\b",
            r"\bПВП\b",
            r"\bfluidized\s+bed\s+furnace\b",
            r"\bFBF\b",
            r"\bавтокл[аыуеовымымиахав]*\b",
            r"\bреактор[аыуеовымымиах]*\b",
            r"\bсгуститель[яыуеовымиахям]*\b",
            r"\bфильтр-пресс[аыуеовымымиах]*\b",
            r"\bпечь\s+кипящего\s+слоя\b",
            r"\bшахтная\s+печь\b",
            r"\bотражательная\s+печь\b",
            r"\bконвертер[аыуеовымымиах]*\b",
        ]
        for pattern in equipment:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "EQUIPMENT",
                    "source": "regex"
                })
        
        # 5. Числовые ограничения (МАКСИМАЛЬНО ПОЛНЫЕ)
        numeric_patterns = [
            # С операторами
            r"[≤<>=]+\s*\d+\.?\d*\s*(?:мг/л|мг/дм³|°C|т/сут|м³/ч|кПа|%|м/с|атм|бар|Па)",
            # Диапазоны
            r"\d+\.?\d*\s*[–-]\s*\d+\.?\d*\s*(?:мг/л|мг/дм³|°C|т/сут|м/с|кПа|%|час|мин)",
            # "от X до Y"
            r"(?:от\s+)?\d+\.?\d*\s+(?:до|–|-)\s*\d+\.?\d*\s*(?:мг/л|°C|т/сут|м/с|кПа|%)",
            # Проценты
            r"\d+\.?\d*\s*%",
            # Время
            r"\d+\.?\d*\s*(?:час[аов]*|минут[аы]|сут[аок]|дн[яей])",
            # Температура
            r"\d{2,4}\s*°?\s*[CcСс]\b",
            # Давление
            r"\d+\.?\d*\s*(?:атм|бар|Па|кПа|МПа)\b",
        ]
        for pattern in numeric_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "label": "NUMERIC_CONSTRAINT",
                    "source": "regex"
                })
        
        # 6. География
        geo_patterns = [
            (r"\b(?:Россия|РФ|СССР|Сибирь|Урал|Норильск|Кольский|Мурманск|Красноярск)\b", "RU"),
            (r"\b(?:США|USA|Канада|Китай|China|Австралия|Чили|Казахстан|ЮАР|Бразилия|Индия)\b", "INTL"),
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
        
        # 8. Удаление дубликатов
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