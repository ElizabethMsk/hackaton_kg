from pyvis.network import Network
from neo4j import GraphDatabase
import json
import os

# Загружаем конфиг
config_path = os.path.join(os.path.dirname(__file__), 'ml', 'config.py')
config = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), config)

NEO4J_URI = config.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = config.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = config.get('NEO4J_PASSWORD', 'test1234')

print("Подключение к Neo4j...")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))