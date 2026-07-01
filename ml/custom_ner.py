import spacy
import re
from typing import List, Dict

class MaterialNER:
    """Простой NER на regex"""
    
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_lg")
    
    def extract(self, text: str) -> List[Dict]:
        entities = []
        
        # Стандартные сущности spaCy
        doc = self.nlp(text)
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "source": "spacy"
            })
        
        # Regex для сплавов
        alloy_pattern = r"(?:[Сс]таль|[Сс]т\.?)\s*\d+[А-Яа-яA-Za-z]?"
        for match in re.finditer(alloy_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "ALLOY",
                "source": "regex"
            })
        
        # Regex для температур
        temp_pattern = r"\d{2,4}\s*°?\s*[CcСс]"
        for match in re.finditer(temp_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "TEMPERATURE",
                "source": "regex"
            })
        
        # Regex для свойств
        prop_pattern = r"\d+\.?\d*\s*(?:HRC|HB|HV|МПа|ГПа)"
        for match in re.finditer(prop_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "PROPERTY_VALUE",
                "source": "regex"
            })
        
        # Удаляем дубликаты
        seen = set()
        unique = []
        for ent in entities:
            key = (ent["text"], ent["label"])
            if key not in seen:
                seen.add(key)
                unique.append(ent)
        
        return unique


if __name__ == "__main__":
    ner = MaterialNER()
    
    test_text = """
    Сталь 45 была подвергнута закалке при температуре 850°C.
    После отпуска при 200°C твёрдость составила 58 HRC.
    """
    
    entities = ner.extract(test_text)
    
    print(f"Найдено {len(entities)} сущностей:\n")
    for ent in entities:
        print(f"  [{ent['label']:15}] {ent['text']:30} ({ent['source']})")