"""
Запуск: python run_all.py --data_path "путь/к/папке/с/яндекс/диска"

Обходит все папки (Доклады, Журналы, Статьи, Обзоры, Материалы конференций),
парсит каждый PDF, прогоняет через pipeline, сохраняет результаты.
"""

import os
import json
import argparse
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml.pipeline import MLPipeline
from ml.search import SemanticSearch

# Папки с данными и их тип документа
FOLDER_TYPES = {
    "Доклады":                  "доклад",
    "Журналы":                  "журнал",
    "Статьи":                   "статья",
    "Обзоры":                   "обзор",
    "Материалы конференций":    "конференция",
}

def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        import pdfminer.high_level
        text = pdfminer.high_level.extract_text(pdf_path)
        return (text or "")[:900000]  # лимит для spaCy
    except Exception as e:
        print(f"  ⚠️  Не удалось прочитать {pdf_path}: {e}")
        return ""

def main(data_path: str):
    pipeline = MLPipeline()
    search   = SemanticSearch()

    all_entities = []   # все сущности из всех документов
    total_docs   = 0
    total_errors = 0

    print(f"\n📂 Обрабатываем данные из: {data_path}\n")

    for folder_name, doc_type in FOLDER_TYPES.items():
        folder_path = Path(data_path) / folder_name

        if not folder_path.exists():
            print(f"⚠️  Папка не найдена: {folder_path}")
            continue

        pdf_files = list(folder_path.glob("*.pdf")) + list(folder_path.glob("*.PDF"))
        print(f"📁 {folder_name} ({len(pdf_files)} файлов)")

        for pdf_file in pdf_files:
            print(f"  → {pdf_file.name}")

            # 1. Извлекаем текст
            text = extract_text_from_pdf(str(pdf_file))
            if not text.strip():
                print(f"     ⚠️  Пустой текст, пропускаем")
                total_errors += 1
                continue

            # 2. Прогоняем через ML pipeline
            try:
                result = pipeline.process_document(text)
            except Exception as e:
                print(f"     ❌ Ошибка pipeline: {e}")
                total_errors += 1
                continue

            # 3. Добавляем метаданные к каждой сущности
            metadata = {
                "source_type": doc_type,
                "filename":    pdf_file.name,
                "folder":      folder_name,
            }
            for ent in result.get("entities", []):
                ent["metadata"] = metadata
                all_entities.append(ent)

            # 4. Добавляем чанки в векторную базу (Chroma)
            chunks = result.get("chunks", [])
            if chunks:
                try:
                    search.add_documents(
                        texts=chunks,
                        metadatas=[metadata] * len(chunks)
                    )
                except Exception as e:
                    print(f"     ⚠️  Ошибка добавления в Chroma: {e}")

            total_docs += 1
            print(f"     ✅ Сущностей: {len(result.get('entities', []))}, чанков: {len(chunks)}")

    # 5. Сохраняем все сущности в entities.json
    output = {
        "total_documents": total_docs,
        "total_errors":    total_errors,
        "total_entities":  len(all_entities),
        "entities":        all_entities,
    }

    with open("entities.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ Готово!")
    print(f"   Документов обработано: {total_docs}")
    print(f"   Ошибок: {total_errors}")
    print(f"   Всего сущностей: {len(all_entities)}")
    print(f"   Сохранено в: entities.json + vector_db/")
    print(f"\n📌 Теперь запушь в git:")
    print(f"   git add entities.json vector_db/")
    print(f"   git commit -m 'add processed entities and vectors'")
    print(f"   git push")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        type=str,
        required=True,
        help="Путь к папке с данными (где лежат Доклады, Журналы, Статьи...)"
    )
    args = parser.parse_args()
    main(args.data_path)