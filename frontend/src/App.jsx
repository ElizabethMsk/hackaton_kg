import { useState, useRef, useEffect } from "react";
import { Network } from "vis-network";

//Фейковые данные для результатов поиска
const FAKE_DATA = [
  {
    id: 1,
    material: "золото",
    regime: "Отжиг 1050°C",
    property: "Коррозионная стойкость",
    summary:
      "Отжиг при 1050°C повысил коррозионную стойкость за счёт растворения карбидов хрома по границам зёрен.",
    sources: [
      "Отчёт №142, лаб. металловедения, 2021",
      "Статья: Жаростойкие стали, 2019",
    ],
  },
  {
    id: 2,
    material: "Сплав ВТ6",
    regime: "Закалка + старение",
    property: "Предел прочности",
    summary:
      "Двухступенчатая термообработка увеличила предел прочности титанового сплава на ~15%.",
    sources: ["Эксперимент E-088, 2022"],
  },
  {
    id: 3,
    material: "Сплав 12Х18Н10Т",
    regime: "Холодная прокатка",
    property: "Твёрдость",
    summary:
      "Холодная деформация повысила твёрдость, но снизила пластичность. Данных по усталости мало.",
    sources: ["Отчёт №77, 2020"],
  },
];

//Данные графа: узлы (кружки) и рёбра (связи между ними)
const GRAPH_NODES = [
  { id: "m1", label: "золото", group: "material" },
  { id: "m2", label: "Сплав ВТ6", group: "material" },
  { id: "m3", label: "12Х18Н10Т", group: "material" },
  { id: "r1", label: "Отжиг 1050°C", group: "regime" },
  { id: "r2", label: "Закалка+старение", group: "regime" },
  { id: "r3", label: "Холодная прокатка", group: "regime" },
  { id: "p1", label: "Коррозионная стойкость", group: "property" },
  { id: "p2", label: "Предел прочности", group: "property" },
  { id: "p3", label: "Твёрдость", group: "property" },
  { id: "e1", label: "Отчёт №142", group: "document" },
  { id: "e2", label: "Эксперимент E-088", group: "document" },
];

const GRAPH_EDGES = [
  { from: "m1", to: "r1" },
  { from: "r1", to: "p1" },
  { from: "m1", to: "e1" },
  { from: "m2", to: "r2" },
  { from: "r2", to: "p2" },
  { from: "m2", to: "e2" },
  { from: "m3", to: "r3" },
  { from: "r3", to: "p3" },
];

//Цвета для каждого типа узла
const GROUP_STYLES = {
  material: { color: "#435983", shape: "box" },
  regime: { color: "#e4f643", shape: "box" },
  property: { color: "#52dc95", shape: "box" },
  document: { color: "#d7b2eb", shape: "box" },
};

//Находит id узлов, которые надо подсветить (сами совпавшие + их прямые соседи)
function getHighlightIds(q) {
  if (q === "") return null;

  //сначала какие узлы сами совпали с запросом
  const matched = new Set(
    GRAPH_NODES.filter((n) => n.label.toLowerCase().includes(q)).map(
      (n) => n.id,
    ),
  );

  //к ним добавляем соседей по рёбрам
  const ids = new Set(matched);
  GRAPH_EDGES.forEach((e) => {
    if (matched.has(e.from)) ids.add(e.to);
    if (matched.has(e.to)) ids.add(e.from);
  });

  return ids;
}

//Строит массив узлов (highlightIds === null -> все яркие. Иначе яркие только те узлы, чей id есть в наборе)
function buildNodes(highlightIds) {
  return GRAPH_NODES.map((n) => {
    const isOn = highlightIds === null || highlightIds.has(n.id);
    return {
      ...n,
      color: isOn ? GROUP_STYLES[n.group].color : "#dcdce5",
      shape: GROUP_STYLES[n.group].shape,
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

  //закладка, где будет "жить" граф
  const graphRef = useRef(null);
  //закладка на сам граф, чтобы потом его обновлять при поиске (перерисовывать)
  const networkRef = useRef(null);

  //запускается один раз после отрисовки - строит граф
  useEffect(() => {
    if (!graphRef.current) return;

    const data = { nodes: buildNodes(null), edges: GRAPH_EDGES };

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
    networkRef.current = network; //сохраняем граф для обновлений

    //клик по узлу => запоминаем, какой выбрали
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const clickedId = params.nodes[0];
        const node = GRAPH_NODES.find((n) => n.id === clickedId);
        setSelectedNode(node);
      } else {
        setSelectedNode(null);
      }
    });

    //уборка при перерисовке
    return () => network.destroy();
  }, []);

  function handleSearch() {
    const q = query.trim().toLowerCase();
    if (q === "") {
      setResults([]);
      //сбрасываем подсветку графа (все узлы снова яркие)
      if (networkRef.current) {
        networkRef.current.setData({
          nodes: buildNodes(null),
          edges: GRAPH_EDGES,
        });
      }
      return;
    }
    const found = FAKE_DATA.filter(
      (item) =>
        item.material.toLowerCase().includes(q) ||
        item.regime.toLowerCase().includes(q) ||
        item.property.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q),
    );
    setResults(found);

    //подсвечиваем в графе узлы, подходящие под запрос
    if (networkRef.current) {
      networkRef.current.setData({
        nodes: buildNodes(getHighlightIds(q)),
        edges: GRAPH_EDGES,
      });
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
          {results === null && (
            <p style={styles.hint}>Введите запрос и нажмите «Найти»</p>
          )}

          {results !== null && results.length === 0 && (
            <p style={styles.empty}>
              Ничего не найдено. Возможно, по этому запросу данных пока мало.
            </p>
          )}

          {results !== null &&
            results.map((item) => (
              <div key={item.id} style={styles.card}>
                <div style={styles.cardTags}>
                  <span style={styles.tagMaterial}>{item.material}</span>
                  <span style={styles.tagRegime}>{item.regime}</span>
                  <span style={styles.tagProperty}>{item.property}</span>
                </div>
                <p style={styles.cardSummary}>{item.summary}</p>
                <div style={styles.sources}>
                  <strong>Источники:</strong>
                  <ul style={styles.sourceList}>
                    {item.sources.map((src, i) => (
                      <li key={i}>{src}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
        </div>

        {/* Граф связей */}
        <h2 style={styles.graphTitle}>Карта связей</h2>
        <div style={styles.graphWrapper}>
          <div ref={graphRef} style={styles.graph} />

          {/* Панель деталей выбранного узла */}
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
                Тип: {translateGroup(selectedNode.group)}
              </p>
              <p style={styles.detailHint}>
                Здесь появятся связанные документы, история и пробелы в данных.
              </p>
            </div>
          )}
        </div>

        {/* Легенда: что значат цвета */}
        <div style={styles.legend}>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#435983" }} />{" "}
            Материал
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#e4f643" }} />{" "}
            Режим
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#52dc95" }} />{" "}
            Свойство
          </span>
          <span style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: "#d7b2eb" }} />{" "}
            Документ
          </span>
        </div>
      </div>
    </div>
  );
}

//переводит код группы в русское слово
function translateGroup(group) {
  const map = {
    material: "Материал",
    regime: "Режим обработки",
    property: "Свойство",
    document: "Документ",
  };
  return map[group] || group;
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

  //стили графа
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
