import { useState, useRef, useEffect } from "react";
import { Network } from "vis-network";

const API_URL = "http://127.0.0.1:8000";

const GROUP_STYLES = {
  ALLOY:          { color: "#435983" },
  MATERIAL:       { color: "#435983" },
  material:       { color: "#435983" },
  PROPERTY:       { color: "#52dc95" },
  PROPERTY_VALUE: { color: "#7fd8a8" },
  property:       { color: "#52dc95" },
  ORG:            { color: "#e4f643" },
  organization:   { color: "#e4f643" },
  PER:            { color: "#d7b2eb" },
  researcher:     { color: "#d7b2eb" },
  LOC:            { color: "#6fb8e0" },
  location:       { color: "#6fb8e0" },
  regime:         { color: "#f18a52" },
  other:          { color: "#aaaaaa" },
};

function getColor(type) {
  return (GROUP_STYLES[type] || GROUP_STYLES.other).color;
}

function getHighlightIds(q, nodes, edges) {
  if (!q) return null;
  const matched = new Set(
    nodes.filter((n) => (n.label || "").toLowerCase().includes(q)).map((n) => n.id)
  );
  const ids = new Set(matched);
  edges.forEach((e) => {
    if (matched.has(e.from)) ids.add(e.to);
    if (matched.has(e.to))   ids.add(e.from);
  });
  return ids;
}

function buildVisNodes(nodes, highlightIds) {
  return nodes.map((n) => {
    const isOn = highlightIds === null || highlightIds.has(n.id);
    return {
      id:     n.id,
      label:  n.label,
      color:  isOn ? getColor(n.type || n.group) : "#dcdce5",
      shape:  "box",
      font:   { color: isOn ? "#1a1a2e" : "#b0b0b0", size: 14 },
      size:   18,
      shadow: { enabled: true, size: 8, color: "rgba(0,0,0,0.2)" },
    };
  });
}

function translateGroup(group) {
  const map = {
    ALLOY: "Сплав", material: "Материал",
    PROPERTY: "Свойство", PROPERTY_VALUE: "Значение свойства", property: "Свойство",
    ORG: "Организация", organization: "Организация",
    PER: "Человек", researcher: "Исследователь",
    LOC: "Место", location: "Локация",
    regime: "Режим",
  };
  return map[group] || group || "—";
}

function App() {
  const [query,        setQuery]        = useState("");
  const [results,      setResults]      = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphData,    setGraphData]    = useState({ nodes: [], edges: [] });

  const graphRef   = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/graph`)
      .then((r) => r.json())
      .then((data) => setGraphData({ nodes: data.nodes || [], edges: data.edges || [] }))
      .catch(() => setGraphData({ nodes: [], edges: [] }));
  }, []);

  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;

    const data = {
      nodes: buildVisNodes(graphData.nodes, null),
      edges: graphData.edges,
    };

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
      layout: { randomSeed: 42 },
    };

    if (networkRef.current) networkRef.current.destroy();
    const network = new Network(graphRef.current, data, options);
    networkRef.current = network;

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const node = graphData.nodes.find((n) => n.id === params.nodes[0]);
        setSelectedNode(node || null);
      } else {
        setSelectedNode(null);
      }
    });

    return () => network.destroy();
  }, [graphData]);

  async function handleSearch() {
    const q = query.trim();
    if (!q) {
      setResults([]);
      if (networkRef.current) {
        networkRef.current.setData({
          nodes: buildVisNodes(graphData.nodes, null),
          edges: graphData.edges,
        });
      }
      return;
    }

    if (networkRef.current) {
      networkRef.current.setData({
        nodes: buildVisNodes(graphData.nodes, getHighlightIds(q.toLowerCase(), graphData.nodes, graphData.edges)),
        edges: graphData.edges,
      });
    }

    setLoading(true);
    try {
      const res  = await fetch(`${API_URL}/search`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ query: q, n_results: 5 }),
      });
      const data = await res.json();
      setResults(data.results || []);
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
        <p style={styles.subtitle}>Спросите, что уже делали с материалом, режимом или свойством</p>

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

        <div style={styles.resultsArea}>
          {loading && <p style={styles.hint}>Ищу…</p>}
          {!loading && results === null && <p style={styles.hint}>Введите запрос и нажмите «Найти»</p>}
          {!loading && results !== null && results.length === 0 && (
            <p style={styles.empty}>Ничего не найдено. Возможно, по этому запросу данных пока мало.</p>
          )}
          {!loading && results !== null && results.map((item, idx) => (
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
              <p style={styles.cardSummary}>{item.document || item.text || item.summary || "—"}</p>
              {item.metadata?.filename && (
                <div style={styles.sources}>
                  <strong>Источник:</strong> {item.metadata.filename}
                  {item.metadata.folder && ` (${item.metadata.folder})`}
                </div>
              )}
            </div>
          ))}
        </div>

        <h2 style={styles.graphTitle}>Карта связей</h2>
        {graphData.nodes.length === 0 && <p style={styles.hint}>Граф загружается или данных пока нет...</p>}
        <div style={styles.graphWrapper}>
          <div ref={graphRef} style={styles.graph} />
          {selectedNode && (
            <div style={styles.detailPanel}>
              <div style={styles.detailClose} onClick={() => setSelectedNode(null)}>✕</div>
              <h3 style={styles.detailTitle}>{selectedNode.label}</h3>
              <p style={styles.detailType}>Тип: {translateGroup(selectedNode.type || selectedNode.group)}</p>
              <p style={styles.detailHint}>Связанные документы, история и пробелы в данных.</p>
            </div>
          )}
        </div>

        <div style={styles.legend}>
          {[
            ["#435983", "Сплав/Материал"],
            ["#e4f643", "Организация"],
            ["#d7b2eb", "Исследователь"],
            ["#6fb8e0", "Место"],
            ["#52dc95", "Свойство"],
            ["#f18a52", "Режим"],
          ].map(([color, label]) => (
            <span key={label} style={styles.legendItem}>
              <span style={{ ...styles.legendDot, background: color }} /> {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
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