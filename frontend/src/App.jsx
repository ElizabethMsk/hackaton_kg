import { useState, useRef, useEffect } from "react";
import { Network } from "vis-network";

const API_URL = "http://localhost:8000";

//Цвета для типов узлов
const GROUP_STYLES = {
  ALLOY: { color: "#435983", shape: "box" },
  PROPERTY: { color: "#52dc95", shape: "box" },
  PROPERTY_VALUE: { color: "#7fd8a8", shape: "box" },
  ORG: { color: "#e08a3c", shape: "box" },
  PER: { color: "#d7b2eb", shape: "box" },
  LOC: { color: "#6fb8e0", shape: "box" },
  UNKNOWN: { color: "#b0b0b8", shape: "box" },
};

const DEFAULT_STYLE = { color: "#b0b0b8", shape: "box" };

function styleFor(node) {
  const key = node.type || node.group;
  return GROUP_STYLES[key] || DEFAULT_STYLE;
}

//Находит id узлов для подсветки (совпавшие + прямые соседи)
function getHighlightIds(q, nodesData, edgesData) {
  if (q === "") return null;

  const matched = new Set(
    nodesData
      .filter((n) => (n.label || "").toLowerCase().includes(q))
      .map((n) => n.id),
  );

  const ids = new Set(matched);
  edgesData.forEach((e) => {
    if (matched.has(e.from)) ids.add(e.to);
    if (matched.has(e.to)) ids.add(e.from);
  });

  return ids;
}

function buildNodes(nodesData, highlightIds) {
  return nodesData.map((n) => {
    const isOn = highlightIds === null || highlightIds.has(n.id);
    const st = styleFor(n);
    return {
      id: n.id,
      label: n.label,
      color: isOn ? st.color : "#dcdce5",
      shape: st.shape,
      font: { color: isOn ? "#1a1a2e" : "#b0b0b0", size: 14 },
      size: 18,
      shadow: { enabled: true, size: 8, color: "rgba(0,0,0,0.2)" },
    };
  });
}

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });

  const graphRef = useRef(null);
  const networkRef = useRef(null);

  //Загружаем граф с бэка при старте
  useEffect(() => {
    async function loadGraph() {
      try {
        const res = await fetch(`${API_URL}/graph`);
        const data = await res.json();
        setGraphData({
          nodes: data.nodes || [],
          edges: data.edges || [],
        });
      } catch (err) {
        console.error("Не удалось загрузить граф с бэка:", err);
      }
    }
    loadGraph();
  }, []);

  //Рисуем граф, когда данные пришли
  useEffect(() => {
    if (!graphRef.current) return;
    if (graphData.nodes.length === 0) return;

    const data = {
      nodes: buildNodes(graphData.nodes, null),
      edges: graphData.edges,
    };

    const options = {
      nodes: { borderWidth: 0 },
      edges: {
        color: "#f18a52",
        width: 2,
        smooth: { type: "cubicBezier" },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      },
      physics: { stabilization: true },
      interaction: { hover: true },
      layout: {
        hierarchical: {
          enabled: true,
          direction: "UD",
          sortMethod: "directed",
          levelSeparation: 120,
          nodeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true,
        },
      },
    };

    const network = new Network(graphRef.current, data, options);
    networkRef.current = network;

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const clickedId = params.nodes[0];
        const node = graphData.nodes.find((n) => n.id === clickedId);
        setSelectedNode(node);
      } else {
        setSelectedNode(null);
      }
    });

    return () => network.destroy();
  }, [graphData]);

  async function handleSearch() {
    const q = query.trim().toLowerCase();

    //подсветка графа
    if (networkRef.current) {
      networkRef.current.setData({
        nodes: buildNodes(
          graphData.nodes,
          getHighlightIds(q, graphData.nodes, graphData.edges),
        ),
        edges: graphData.edges,
      });
    }

    if (q === "") {
      setResults([]);
      return;
    }

    //реальный поиск через бэк
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), n_results: 5 }),
      });
      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      console.error("Ошибка поиска на бэке:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.background}>
      <div style={styles.page}>
        <h1 style={styles.title}> The Scientific Tangle by Rassol</h1>
        <p style={styles.subtitle}>
          Спросите, что уже делали с материалом, режимом или свойством
        </p>

        {/* Поисковая строка */}
        <div style={styles.searchRow}>
          <input
            style={styles.input}
            type="text"
            placeholder="Например: золото"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
          />
          <button style={styles.button} onClick={handleSearch}>
            Найти
          </button>
        </div>

        {/* Область результатов */}
        <div style={styles.resultsArea}>
          {loading && <p style={styles.hint}>Ищу…</p>}

          {!loading && results === null && (
            <p style={styles.hint}>Введите запрос и нажмите «Найти»</p>
          )}

          {!loading && results !== null && results.length === 0 && (
            <p style={styles.empty}>
              Ничего не найдено. Возможно, по этому запросу данных пока мало.
            </p>
          )}

          {!loading &&
            results !== null &&
            results.map((item, idx) => (
              <div key={item.id || idx} style={styles.card}>
                <div style={styles.cardTags}>
                  {item.material && (
                    <span style={styles.tagMaterial}>{item.material}</span>
                  )}
                  {item.regime && (
                    <span style={styles.tagRegime}>{item.regime}</span>
                  )}
                  {item.property && (
                    <span style={styles.tagProperty}>{item.property}</span>
                  )}
                </div>
                <p style={styles.cardSummary}>
                  {item.summary || item.text || item.document || ""}
                </p>
                {item.sources && (
                  <div style={styles.sources}>
                    <strong>Источники:</strong>
                    <ul style={styles.sourceList}>
                      {item.sources.map((src, i) => (
                        <li key={i}>{src}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* Граф связей */}
        <h2 style={styles.graphTitle}>Карта связей</h2>
        <div style={styles.graphWrapper}>
          <div ref={graphRef} style={styles.graph} />

          {selectedNode && (
            <div style={styles.detailPanel}>
              <div
                style={styles.detailClose}
                onClick={() => setSelectedNode(null)}
              >
                ✕
              </div>
              <h3 style={styles.detailTitle}>{selectedNode.label}</h3>
              <p style={styles.detailType}>
                Тип: {translateGroup(selectedNode.type || selectedNode.group)}
              </p>
              <p style={styles.detailHint}>
                Здесь появятся связанные документы, история и пробелы в данных.
              </p>
            </div>
          )}
        </div>

        {/* Легенда */}
        <div style={styles.legend}>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#435983" }} />{" "}
            Сплав
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#52dc95" }} />{" "}
            Свойство
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#e08a3c" }} />{" "}
            Организация
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#d7b2eb" }} />{" "}
            Человек
          </span>
        </div>
      </div>
    </div>
  );
}

function translateGroup(group) {
  const map = {
    ALLOY: "Сплав",
    PROPERTY: "Свойство",
    PROPERTY_VALUE: "Значение свойства",
    ORG: "Организация",
    PER: "Человек",
    LOC: "Место",
    UNKNOWN: "Неизвестно",
  };
  return map[group] || group || "—";
}

const styles = {
  background: {
    minHeight: "100vh",
    background: "#2e4a2e",
    padding: "40px 20px",
  },
  page: {
    maxWidth: 720,
    margin: "0 auto",
    padding: "32px 28px",
    fontFamily: "system-ui, sans-serif",
    color: "#1a1a2e",
    background: "#ffffff",
    borderRadius: 16,
    border: "1px solid #e0e0e0",
    boxShadow: "0 4px 20px rgba(0,0,0,0.06)",
  },
  title: { fontSize: 32, marginBottom: 4, textAlign: "center" },
  subtitle: {
    color: "#666",
    marginTop: 0,
    marginBottom: 24,
    textAlign: "center",
  },
  searchRow: { display: "flex", gap: 8, marginBottom: 28 },
  input: {
    flex: 1,
    padding: "12px 14px",
    fontSize: 16,
    border: "2px solid #ddd",
    borderRadius: 8,
    outline: "none",
  },
  button: {
    padding: "12px 24px",
    fontSize: 16,
    border: "none",
    borderRadius: 8,
    background: "#1e430f",
    color: "white",
    cursor: "pointer",
  },
  resultsArea: { display: "flex", flexDirection: "column", gap: 16 },
  hint: { color: "#999", textAlign: "center" },
  empty: { color: "#c0392b", textAlign: "center" },
  card: {
    border: "1px solid #e0e0e0",
    borderRadius: 12,
    padding: 18,
    background: "#fafaff",
  },
  cardTags: { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 },
  tagMaterial: {
    background: "#e3f2fd",
    color: "#1565c0",
    padding: "4px 10px",
    borderRadius: 20,
    fontSize: 13,
  },
  tagRegime: {
    background: "#fff3e0",
    color: "#e65100",
    padding: "4px 10px",
    borderRadius: 20,
    fontSize: 13,
  },
  tagProperty: {
    background: "#e8f5e9",
    color: "#2e7d32",
    padding: "4px 10px",
    borderRadius: 20,
    fontSize: 13,
  },
  cardSummary: { margin: "0 0 12px", lineHeight: 1.5 },
  sources: { fontSize: 14, color: "#555" },
  sourceList: { margin: "6px 0 0", paddingLeft: 20 },

  graphTitle: {
    fontSize: 22,
    marginTop: 32,
    marginBottom: 12,
    textAlign: "center",
  },
  graphWrapper: { position: "relative" },
  graph: {
    height: 420,
    border: "1px solid #e0e0e0",
    borderRadius: 12,
    background: "#fbfbff",
  },
  detailPanel: {
    position: "absolute",
    top: 12,
    right: 12,
    width: 240,
    background: "white",
    border: "1px solid #ddd",
    borderRadius: 12,
    padding: 16,
    boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
  },
  detailClose: {
    position: "absolute",
    top: 10,
    right: 12,
    cursor: "pointer",
    color: "#999",
  },
  detailTitle: { margin: "0 0 8px", fontSize: 18 },
  detailType: { margin: "0 0 12px", color: "#666", fontSize: 14 },
  detailHint: { margin: 0, color: "#999", fontSize: 13, lineHeight: 1.4 },
  legend: {
    display: "flex",
    gap: 16,
    flexWrap: "wrap",
    justifyContent: "center",
    marginTop: 14,
  },
  legendItem: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 14,
    color: "#555",
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: "50%",
    display: "inline-block",
  },
};

export default App;
