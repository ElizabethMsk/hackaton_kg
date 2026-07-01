from pyvis.network import Network
from neo4j import GraphDatabase
import json

print("Подключение к Neo4j...")
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test1234"))

print("Загрузка данных из графа...")
with driver.session() as session:
    # Получаем все узлы
    result = session.run("MATCH (n) RETURN n")
    nodes = []
    for record in result:
        node = record["n"]
        labels = list(node.labels)
        label = labels[0] if labels else "Unknown"
        nodes.append({
            "id": node.id,
            "label": node["name"],
            "group": label,
            "title": f"{label}: {node['name']}"
        })
    
    # Получаем все связи (пока их нет, но создадим простые)
    # Можно добавить связи позже
    relationships = []

print(f"Загружено {len(nodes)} узлов")

# Создаём интерактивный граф
print("Создание визуализации...")
net = Network(
    height="750px",
    width="100%",
    bgcolor="#222222",
    font_color="white",
    heading="Knowledge Graph - Материалы"
)

# Добавляем узлы
for node in nodes:
    net.add_node(
        node["id"],
        label=node["label"][:50],  # Обрезаем длинные названия
        title=node["title"],
        group=node["group"],
        size=25
    )

# Добавляем связи (если есть)
for rel in relationships:
    net.add_edge(rel["from"], rel["to"])

# Настраиваем физику
net.set_options("""
var options = {
  "nodes": {
    "font": {
      "size": 14,
      "color": "#ffffff"
    }
  },
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.005,
      "springLength": 100,
      "springConstant": 0.18
    },
    "maxVelocity": 50,
    "solver": "forceAtlas2Based",
    "timestep": 0.35,
    "stabilization": {
      "iterations": 150
    }
  }
}
""")

# Сохраняем
net.save_graph("graph_visualization.html")
print("✅ Граф сохранён в: graph_visualization.html")
print("Откройте этот файл в браузере!")

driver.close()