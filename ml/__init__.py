"""
ML-модуль для Knowledge Graph
Хакатон "Научный клубок" 2026
"""

from .mining_ner import MiningNER
from .chunker import TextChunker
from .search import SemanticSearch
from .ranking import ResultRanker
from .gaps import GapAnalyzer
from .pipeline import MLPipeline

__all__ = [
    "MiningNER",
    "TextChunker", 
    "SemanticSearch",
    "ResultRanker",
    "GapAnalyzer",
    "MLPipeline",
]

__version__ = "1.0.0"