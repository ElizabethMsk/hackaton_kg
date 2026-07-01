import re
from typing import List

class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str) -> List[str]:
        """Разбиение по размеру с учётом границ предложений"""
        # Сначала разбиваем на предложения
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Если добавление предложения не превышает размер
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += (" " if current_chunk else "") + sentence
            else:
                # Сохраняем текущий чанк
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Начинаем новый чанк с перекрытием
                # Берём последние chunk_overlap символов из предыдущего
                if len(current_chunk) > self.chunk_overlap:
                    current_chunk = current_chunk[-self.chunk_overlap:] + " " + sentence
                else:
                    current_chunk = sentence
        
        # Не забываем последний чанк
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


if __name__ == "__main__":
    chunker = TextChunker(chunk_size=200, chunk_overlap=30)
    
    text = """
    Сталь 45 подвергалась закалке при температуре 850°C. 
    Время выдержки составляло 2 часа. 
    После закалки твёрдость достигла 58 HRC.
    
    Отпуск проводился при 200°C в течение 1 часа.
    Итоговая твёрдость после отпуска — 55 HRC.
    """
    
    chunks = chunker.chunk(text)
    
    print(f"Текст разбит на {len(chunks)} чанков:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Чанк {i} ({len(chunk)} символов) ---")
        print(chunk)
        print()