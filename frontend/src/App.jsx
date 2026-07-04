import { useState, useRef, useEffect } from "react";
import { Network } from "vis-network";

// ── Адрес бека ───────────────────────────────────────────────
const API = "http://127.0.0.1:8000";

// Цвета для каждого типа узла

const GROUP_STYLES = {
  material:     { color: "#435983" },
  researcher:   { color: "#d7b2eb" },
  organization: { color: "#e4f643" },
  location:     { color: "#52dc95" },
  regime:       { color: "#f18a52" },
  property:     { color: "#52dc95" },
  other:        { color: "#aaaaaa" },
};

function getNodeColor(type) {
  return (GROUP_STYLES[type] || GROUP_STYLES.DEFAULT).color;
}

// Находит id узлов для подсветки по запросу
function getHighlightIds(q, nodes, edges) {
  if (!q) return null;
  const matched = new Set(
    nodes.filter((n) => n.label?.toLowerCase().includes(q)).map((n) => n.id)
  );
  const ids = new Set(matched);
  edges.forEach((e) => {
    if (matched.has(e.from)) ids.add(e.to);
    if (matched.has(e.to))   ids.add(e.from);
  });
  return ids;
}

// Строит массив vis-узлов с подсветкой
function buildVisNodes(nodes, highlightIds) {
  return nodes.map((n) => {
    const isOn = highlightIds === null || highlightIds.has(n.id);
    return {
      id:    n.id,
      label: n.label,
      group: n.type,
      color: isOn ? getNodeColor(n.type) : "#dcdce5",
      shape: "box",
      font:  { color: isOn ? "#1a1a2e" : "#b0b0b0", size: 14 },
      size:  18,
      shadow: { enabled: true, size: 8, color: "rgba(0,0,0,0.2)" },
    };
  });
}

function App() {
  const [query,        setQuery]        = useState("");
  const [results,      setResults]      = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphNodes,   setGraphNodes]   = useState([]);
  const [graphEdges,   setGraphEdges]   = useState([]);

  const graphRef   = useRef(null);
  const networkRef = useRef(null);

  // ── Загружаем граф при старте ────────────────────────────
  useEffect(() => {
    fetch(`${API}/graph`)
      .then((r) => r.json())
      .then((data) => {
        setGraphNodes(data.nodes || []);
        setGraphEdges(data.edges || []);
      })
      .catch(() => {
        // если бек недоступен — граф остаётся пустым
        setGraphNodes([]);
        setGraphEdges([]);
      });
  }, []);

  // ── Строим/обновляем vis-network когда меняются данные графа ──
  useEffect(() => {
    if (!graphRef.current) return;

    const visNodes = buildVisNodes(graphNodes, null);
    const data     = { nodes: visNodes, edges: graphEdges };

    const options = {
      nodes: { borderWidth: 0 },
      edges: {
        color:  "#f18a52",
        width:  2,
        smooth: { type: "cubicBezier" },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      },
      physics: {
  enabled: true,
  solver: "forceAtlas2Based",
  stabilization: { iterations: 200 },
},
interaction: { hover: true },
layout: {
  randomSeed: 42,
},
    };

    if (networkRef.current) networkRef.current.destroy();
    const network    = new Network(graphRef.current, data, options);
    networkRef.current = network;

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const clickedId = params.nodes[0];
        const node      = graphNodes.find((n) => n.id === clickedId);
        setSelectedNode(node || null);
      } else {
        setSelectedNode(null);
      }
    });

    return () => network.destroy();
  }, [graphNodes, graphEdges]);

  // ── Поиск ───────────────────────────────────────────────
  async function handleSearch() {
    const q = query.trim();
    if (!q) {
      setResults([]);
      if (networkRef.current) {
        networkRef.current.setData({
          nodes: buildVisNodes(graphNodes, null),
          edges: graphEdges,
        });
      }
      return;
    }

    setLoading(true);
    try {
      const res  = await fetch(`${API}/search`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ query: q, n_results: 5 }),
      });
      const data = await res.json();
      setResults(data.results || []);

      // подсвечиваем в графе
      if (networkRef.current) {
        const highlightIds = getHighlightIds(q.toLowerCase(), graphNodes, graphEdges);
        networkRef.current.setData({
          nodes: buildVisNodes(graphNodes, highlightIds),
          edges: graphEdges,
        });
      }
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.background}>
      <div style={styles.page}>
        <h1 style={styles.title}>The Scientific Tangle by Rassol</h1>
        <p style={styles.subtitle}>
          Спросите, что уже делали с материалом, режимом или свойством
        </p>

        {/* Поисковая строка */}
        <div style={styles.searchRow}>
          <input
            style={styles.input}
            type="text"
            placeholder="Например: электроэкстракция никеля"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
          />
          <button style={styles.button} onClick={handleSearch} disabled={loading}>
            {loading ? "Ищу..." : "Найти"}
          </button>
        </div>

        {/* Результаты */}
        <div style={styles.resultsArea}>
          {results === null && (
            <p style={styles.hint}>Введите запрос и нажмите «Найти»</p>
          )}

          {results !== null && results.length === 0 && !loading && (
            <p style={styles.empty}>
              Ничего не найдено. Возможно, по этому запросу данных пока мало.
            </p>
          )}

          {results !== null &&
            results.map((item, idx) => (
              <div key={idx} style={styles.card}>
                <div style={styles.cardTags}>
                  {item.metadata?.source_type && (
                    <span style={styles.tagMaterial}>{item.metadata.source_type}</span>
                  )}
                  {item.similarity !== undefined && (
                    <span style={styles.tagProperty}>
                      Релевантность: {Math.round(item.similarity * 100)}%
                    </span>
                  )}
                </div>
                <p style={styles.cardSummary}>
                  {item.document || item.text || "—"}
                </p>
                {item.metadata?.filename && (
                  <div style={styles.sources}>
                    <strong>Источник:</strong> {item.metadata.filename}
                    {item.metadata.folder && ` (${item.metadata.folder})`}
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* Граф */}
        <h2 style={styles.graphTitle}>Карта связей</h2>
        {graphNodes.length === 0 && (
          <p style={styles.hint}>Граф загружается или данных пока нет...</p>
        )}
        <div style={styles.graphWrapper}>
          <div ref={graphRef} style={styles.graph} />

          {selectedNode && (
            <div style={styles.detailPanel}>
              <div style={styles.detailClose} onClick={() => setSelectedNode(null)}>✕</div>
              <h3 style={styles.detailTitle}>{selectedNode.label}</h3>
              <p style={styles.detailType}>Тип: {selectedNode.type || "—"}</p>
              <p style={styles.detailHint}>
                Связанные документы, история и пробелы в данных.
              </p>
            </div>
          )}
        </div>

        {/* Легенда */}
        <div style={styles.legend}>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#435983" }} /> Материал
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#e4f643" }} /> Режим
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#52dc95" }} /> Свойство
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#d7b2eb" }} /> Документ
          </span>
        </div>
      </div>
    </div>
  );
}

function translateGroup(group) {
  const map = {
    material: "Материал",
    regime:   "Режим обработки",
    property: "Свойство",
    document: "Документ",
  };
  return map[group] || group;
}

const styles = {
  background:   { minHeight: "100vh", background: "#2e4a2e", padding: "40px 20px" },
  page:         { maxWidth: 720, margin: "0 auto", padding: "32px 28px", fontFamily: "system-ui, sans-serif", color: "#1a1a2e", background: "#ffffff", borderRadius: 16, border: "1px solid #e0e0e0", boxShadow: "0 4px 20px rgba(0,0,0,0.06)" },
  title:        { fontSize: 32, marginBottom: 4, textAlign: "center" },
  subtitle:     { color: "#666", marginTop: 0, marginBottom: 24, textAlign: "center" },
  searchRow:    { display: "flex", gap: 8, marginBottom: 28 },
  input:        { flex: 1, padding: "12px 14px", fontSize: 16, border: "2px solid #ddd", borderRadius: 8, outline: "none" },
  button:       { padding: "12px 24px", fontSize: 16, border: "none", borderRadius: 8, background: "#1e430f", color: "white", cursor: "pointer" },
  resultsArea:  { display: "flex", flexDirection: "column", gap: 16 },
  hint:         { color: "#999", textAlign: "center" },
  empty:        { color: "#c0392b", textAlign: "center" },
  card:         { border: "1px solid #e0e0e0", borderRadius: 12, padding: 18, background: "#fafaff" },
  cardTags:     { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 },
  tagMaterial:  { background: "#e3f2fd", color: "#1565c0", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  tagRegime:    { background: "#fff3e0", color: "#e65100", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  tagProperty:  { background: "#e8f5e9", color: "#2e7d32", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  cardSummary:  { margin: "0 0 12px", lineHeight: 1.5 },
  sources:      { fontSize: 14, color: "#555" },
  sourceList:   { margin: "6px 0 0", paddingLeft: 20 },
  graphTitle:   { fontSize: 22, marginTop: 32, marginBottom: 12, textAlign: "center" },
  graphWrapper: { position: "relative" },
  graph:        { height: 420, border: "1px solid #e0e0e0", borderRadius: 12, background: "#fbfbff" },
  detailPanel:  { position: "absolute", top: 12, right: 12, width: 240, background: "white", border: "1px solid #ddd", borderRadius: 12, padding: 16, boxShadow: "0 4px 16px rgba(0,0,0,0.12)" },
  detailClose:  { position: "absolute", top: 10, right: 12, cursor: "pointer", color: "#999" },
  detailTitle:  { margin: "0 0 8px", fontSize: 18 },
  detailType:   { margin: "0 0 12px", color: "#666", fontSize: 14 },
  detailHint:   { margin: 0, color: "#999", fontSize: 13, lineHeight: 1.4 },
  legend:       { display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center", marginTop: 14 },
  legendItem:   { display: "flex", alignItems: "center", gap: 6, fontSize: 14, color: "#555" },
  legendDot:    { width: 12, height: 12, borderRadius: "50%", display: "inline-block" },
};

export default App;