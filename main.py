import json
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Если запускаешь из папки backend/ — этот путь добавит корень проекта в импорты
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.pipeline import MLPipeline
from ml.search import SemanticSearch

# ── Инициализация ────────────────────────────────────────────
app = FastAPI(title="Научный клубок", version="0.1.0")

# CORS — чтобы фронт мог обращаться к беку
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # на проде заменить на конкретный адрес фронта
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем ML-модули один раз при старте
pipeline = MLPipeline()
search   = SemanticSearch()

# Путь до entities.json (лежит в корне репозитория)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTITIES_PATH = os.path.join(ROOT, "entities.json")


# ── Вспомогательные функции ──────────────────────────────────
def load_entities() -> dict:
    """Загружает граф из entities.json"""
    try:
        with open(ENTITIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"nodes": [], "edges": []}
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}


def entities_to_graph(entities: list) -> dict:
    """
    Конвертирует список сущностей из NER в формат {nodes, edges}
    который ждёт Cytoscape.js / vis-network на фронте.
    """
    nodes = []
    edges = []
    seen_ids = set()

    for ent in entities:
        node_id = f"{ent.get('label', 'UNK')}_{ent.get('text', '')}".replace(" ", "_")
        if node_id not in seen_ids:
            nodes.append({
                "id":    node_id,
                "label": ent.get("text", ""),
                "type":  ent.get("label", "UNKNOWN"),
            })
            seen_ids.add(node_id)

    return {"nodes": nodes, "edges": edges}


# ── Схемы запросов ───────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    n_results: int = 5

class ProcessRequest(BaseModel):
    text: str

class GapsRequest(BaseModel):
    materials:   list = []
    properties:  list = []
    experiments: list = []


# ── Эндпоинты ────────────────────────────────────────────────

@app.get("/")
def health():
    """Проверка, что сервер живой"""
    return {"status": "ok", "message": "Научный клубок работает 🔬"}


@app.post("/search")
def semantic_search(req: SearchRequest):
    """
    Семантический поиск по запросу.
    Фронт отправляет: { "query": "электроэкстракция никеля", "n_results": 5 }
    """
    try:
        raw_results = search.search(req.query, n_results=req.n_results)
        ranked      = pipeline.rank_results(req.query, raw_results)
        return {
            "query":   req.query,
            "count":   len(ranked),
            "results": ranked,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")


@app.get("/graph")
def get_graph():
    """
    Отдаёт данные графа для визуализации.
    Возвращает { nodes: [...], edges: [...] }
    """
    data = load_entities()

    # Если entities.json уже в формате {nodes, edges} — отдаём как есть
    if "nodes" in data and "edges" in data:
        return data

    # Если это плоский список сущностей — конвертируем
    if isinstance(data, list):
        return entities_to_graph(data)

    # Если внутри есть поле entities
    if "entities" in data:
        return entities_to_graph(data["entities"])

    return {"nodes": [], "edges": []}


@app.post("/process")
def process_document(req: ProcessRequest):
    """
    Обрабатывает текст: извлекает сущности, разбивает на чанки.
    Фронт отправляет: { "text": "..." }
    """
    try:
        result = pipeline.process_document(req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Загрузка PDF/TXT файла и его обработка.
    Фронт отправляет файл через form-data.
    """
    try:
        content = await file.read()

        # Для TXT — сразу декодируем
        if file.filename.endswith(".txt"):
            text = content.decode("utf-8")

        # Для PDF — нужен pdfminer или pypdf (ML-специалист уже делал в 01_parse.py)
        elif file.filename.endswith(".pdf"):
            try:
                import pdfminer.high_level
                import io
                text = pdfminer.high_level.extract_text(io.BytesIO(content))
            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="Установи pdfminer: pip install pdfminer.six"
                )
        else:
            raise HTTPException(status_code=400, detail="Поддерживаются только PDF и TXT")

        result = pipeline.process_document(text)
        return {
            "filename": file.filename,
            "status":   "processed",
            "result":   result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке: {str(e)}")


@app.post("/gaps")
def analyze_gaps(req: GapsRequest):
    """
    Анализ пробелов в данных.
    Показывает какие комбинации материал+режим+свойство не изучены.
    """
    try:
        summary = pipeline.analyze_gaps(
            req.materials,
            req.properties,
            req.experiments,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа пробелов: {str(e)}")


@app.get("/gaps/auto")
def auto_gaps():
    """
    Автоматический анализ пробелов на основе уже загруженного графа.
    Фронт может вызвать без параметров.
    """
    data = load_entities()
    entities = []

    if isinstance(data, list):
        entities = data
    elif "entities" in data:
        entities = data["entities"]

    materials  = [e["text"] for e in entities if e.get("label") == "ALLOY"]
    properties = [e["text"] for e in entities if e.get("label") in ("PROPERTY", "PROPERTY_VALUE")]

    try:
        summary = pipeline.analyze_gaps(materials, properties, [])
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))