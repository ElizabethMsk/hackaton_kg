import { useState, useRef, useEffect } from "react";
import { Network } from "vis-network";

const API_URL = "http://127.0.0.1:8000";

// Ключевые слова для категоризации терминов
const MATERIAL_ROOTS = ["никел","медн","меди","медь","кобал","платин","золот","серебр","цинк","свинц","желез","алюмин","титан","хром","молибд","палладий","родий","иридий","рутений","файнштейн","штейн","шлак","концентрат","сплав","катод","анод","электролит","сульфат","хлорид","оксид","латерит","пирротин","халькопирит","пентландит","мпг","mpg","nickel","copper","cobalt","platinum","металл","раствор","реагент","кислот","щелоч","сорбент","ионит","смол"];

const PROCESS_ROOTS = ["выщелач","электроэкстракц","электролиз","плавк","рафиниров","флотац","обжиг","восстановл","окислен","экстракц","осажден","фильтрац","переработк","производств","технолог","leaching","smelting","electrowin","сорбц","десорбц","тиокарбамид","тиомочевин","конвертир","обогащ","растворен","хлориров","цементац","дистилл","кристаллиз","электролизн","электролизёр","гидрометаллург","пирометаллург"];

const PROPERTY_ROOTS = ["концентрац","температур","скорост","давлен","содержан","количеств","результат","эффективн","производительн","состав","свойств","показател","параметр","твёрдост","прочност","растворим","селективн","извлечен","плотност","вязкост","кислотност","выход","степен","потер"];
const BAD_ENDINGS = ["ствии","ствие","опреде","ления","тельн"];

function categorizeWord(word) {
  const w = word.toLowerCase();
  // Фильтруем обрывки слов 
  if (BAD_ENDINGS.some(e => w.endsWith(e) && w.length < 8)) return null;
  if (/^[^аеёиоуыьъэюяaeiou]{4,}$/i.test(w)) return null; // нет гласных
  
  if (MATERIAL_ROOTS.some(r => w.startsWith(r))) return { color: "#435983" };
  if (PROCESS_ROOTS.some(r => w.startsWith(r))) return { color: "#f18a52" };
  if (PROPERTY_ROOTS.some(r => w.startsWith(r))) return { color: "#52dc95" };
  return { color: "#b0b8cc" };
}

function buildKeywordGraph(results) {
  const stopWords = new Set(["это","что","как","для","при","или","его","они","все","уже","так","был","но","по","на","из","от","до","за","со","об","не","то","же","бы","ли","и","в","с","к","а","их","он","она","они","мы","вы","был","была","были","быть","также","того","этот","этого","этой","этих","которые","который","которая","которого","после","между","через","может","более","менее","если","когда","тогда","здесь","там","now","the","and","for","with","this","that","from","are","was","were","have","been","their","they","which","показана","представлены","определения","составил","использованием","потенциал","возможность","методом","прямого","таблица","определение"]);

  const wordCount = {};
  results.forEach((item) => {
    const text = (item.document || item.text || "");
    text.split(/[\s,.\-–:;()\[\]\/\n\r]+/).forEach(word => {
      const w = word.toLowerCase().replace(/[«»"']/g, "").replace(/[^\wа-яёА-ЯЁa-zA-Z]/g, "");
      if (w.length > 3 && !stopWords.has(w) && isNaN(w)) {
        wordCount[w] = (wordCount[w] || 0) + 1;
      }
    });
  });

  const topWords = Object.entries(wordCount).sort((a, b) => b[1] - a[1]).slice(0, 35);

  const nodes = topWords.map(([word, count], i) => {
    const { color } = categorizeWord(word);
    return {
      id: `kw_${i}`, label: word,
      color: color, shape: "box",
      font: { color: "#1a1a2e", size: Math.min(11 + count, 16) },
      size: Math.min(12 + count * 2, 28),
      shadow: { enabled: true, size: 6, color: "rgba(0,0,0,0.15)" },
    };
  });

  // Связываем часто встречающиеся узлы
  const edges = [];
  for (let i = 0; i < nodes.length - 1; i += 2) {
    if (nodes[i + 1]) edges.push({ from: nodes[i].id, to: nodes[i + 1].id });
    if (i + 2 < nodes.length && i % 4 === 0) edges.push({ from: nodes[i].id, to: nodes[i + 2].id });
  }

  return { nodes, edges };
}

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const graphRef = useRef(null);
  const networkRef = useRef(null);

  const graphOptions = {
    nodes: { borderWidth: 0 },
    edges: { color: "#d0d8e8", width: 1.5, smooth: { type: "cubicBezier" }, arrows: { to: { enabled: false } } },
    physics: { enabled: true, solver: "forceAtlas2Based", stabilization: { iterations: 150 } },
    interaction: { hover: true },
    layout: { randomSeed: 42 },
  };

  useEffect(() => {
    if (!graphRef.current) return;
    if (networkRef.current) networkRef.current.destroy();
    const network = new Network(graphRef.current, { nodes: [], edges: [] }, graphOptions);
    networkRef.current = network;
    return () => network.destroy();
  }, []);

  function showKeywordGraph(results) {
    if (!networkRef.current) return;
    if (!results || results.length === 0) return;
    const { nodes, edges } = buildKeywordGraph(results);
    networkRef.current.setData({ nodes, edges });
  }

  async function handleSearch() {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setAnswer(null);
      setHasSearched(false);
      if (networkRef.current) networkRef.current.setData({ nodes: [], edges: [] });
      return;
    }
    setLoading(true);
    setAnswer(null);
    setHasSearched(true);
    try {
      const res = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, n_results: 5 }),
      });
      const data = await res.json();
      setResults(data.results || []);
      showKeywordGraph(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk() {
    const q = query.trim();
    if (!q) return;
    setLoadingAnswer(true);
    setAnswer(null);
    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, n_results: 5 }),
      });
      const data = await res.json();
      setAnswer(data.answer || "Не удалось получить ответ.");
    } catch {
      setAnswer("Ошибка при обращении к Yandex GPT.");
    } finally {
      setLoadingAnswer(false);
    }
  }

  return (
    <div style={styles.background}>
      <div style={styles.page}>
        <h1 style={styles.title}>The Scientific Tangle by Rassol</h1>
        <p style={styles.subtitle}>Спросите, что уже делали с материалом, режимом или свойством</p>

        <div style={styles.searchRow}>
          <input style={styles.input} type="text" placeholder="Например: электроэкстракция никеля"
            value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }} />
          <button style={styles.button} onClick={handleSearch} disabled={loading}>{loading ? "Ищу..." : "Найти"}</button>
          <button style={styles.buttonAsk} onClick={handleAsk} disabled={loadingAnswer}>{loadingAnswer ? "Думаю..." : "Ответ ИИ"}</button>
        </div>

        {loadingAnswer && <div style={styles.answerBox}><p style={styles.hint}>Yandex GPT анализирует документы...</p></div>}
        {answer && (
          <div style={styles.answerBox}>
            <div style={styles.answerHeader}>Развёрнутый ответ</div>
            <p style={styles.answerText}>{answer}</p>
          </div>
        )}

        <div style={styles.resultsArea}>
          {loading && <p style={styles.hint}>Ищу…</p>}
          {!loading && results === null && <p style={styles.hint}>Введите запрос и нажмите «Найти»</p>}
          {!loading && results !== null && results.length === 0 && <p style={styles.empty}>Ничего не найдено. Возможно, по этому запросу данных пока мало.</p>}
          {!loading && results !== null && results.map((item, idx) => (
            <div key={idx} style={styles.card}>
              <div style={styles.cardTags}>
                {item.metadata?.source_type && <span style={styles.tagMaterial}>{item.metadata.source_type}</span>}
                {item.similarity !== undefined && <span style={styles.tagProperty}>Релевантность: {Math.round(item.similarity * 100)}%</span>}
              </div>
              <p style={styles.cardSummary}>{item.document || item.text || item.summary || "—"}</p>
              {item.metadata?.filename && (
                <div style={styles.sources}><strong>Источник:</strong> {item.metadata.filename}{item.metadata.folder && ` (${item.metadata.folder})`}</div>
              )}
            </div>
          ))}
        </div>

        <h2 style={styles.graphTitle}>Карта связей</h2>
        {!hasSearched && <p style={styles.hint}>Введите запрос — карта построится по найденным документам</p>}
        <div style={styles.graphWrapper}>
          <div ref={graphRef} style={styles.graph} />
        </div>

        <div style={styles.legend}>
          {[["#435983","Материал/Вещество"],["#f18a52","Процесс/Технология"],["#52dc95","Свойство/Параметр"],["#b0b8cc","Прочие термины"]].map(([color, label]) => (
            <span key={label} style={styles.legendItem}><span style={{ ...styles.legendDot, background: color }} /> {label}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  background: { minHeight: "100vh", background: "#2e4a2e", padding: "40px 20px" },
  page: { maxWidth: 720, margin: "0 auto", padding: "32px 28px", fontFamily: "system-ui, sans-serif", color: "#1a1a2e", background: "#ffffff", borderRadius: 16, border: "1px solid #e0e0e0", boxShadow: "0 4px 20px rgba(0,0,0,0.06)" },
  title: { fontSize: 32, marginBottom: 4, textAlign: "center" },
  subtitle: { color: "#666", marginTop: 0, marginBottom: 24, textAlign: "center" },
  searchRow: { display: "flex", gap: 8, marginBottom: 16 },
  input: { flex: 1, padding: "12px 14px", fontSize: 16, border: "2px solid #ddd", borderRadius: 8, outline: "none" },
  button: { padding: "12px 24px", fontSize: 16, border: "none", borderRadius: 8, background: "#1e430f", color: "white", cursor: "pointer", whiteSpace: "nowrap" },
  buttonAsk: { padding: "12px 20px", fontSize: 16, border: "none", borderRadius: 8, background: "#5c3d8f", color: "white", cursor: "pointer", whiteSpace: "nowrap" },
  answerBox: { background: "#f3eeff", border: "1px solid #c4a8f0", borderRadius: 12, padding: 20, marginBottom: 20 },
  answerHeader: { fontWeight: 700, fontSize: 16, marginBottom: 10, color: "#5c3d8f" },
  answerText: { margin: 0, lineHeight: 1.7, whiteSpace: "pre-wrap", color: "#1a1a2e" },
  resultsArea: { display: "flex", flexDirection: "column", gap: 16 },
  hint: { color: "#999", textAlign: "center" },
  empty: { color: "#c0392b", textAlign: "center" },
  card: { border: "1px solid #e0e0e0", borderRadius: 12, padding: 18, background: "#fafaff" },
  cardTags: { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 },
  tagMaterial: { background: "#e3f2fd", color: "#1565c0", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  tagRegime: { background: "#fff3e0", color: "#e65100", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  tagProperty: { background: "#e8f5e9", color: "#2e7d32", padding: "4px 10px", borderRadius: 20, fontSize: 13 },
  cardSummary: { margin: "0 0 12px", lineHeight: 1.5 },
  sources: { fontSize: 14, color: "#555" },
  graphTitle: { fontSize: 22, marginTop: 32, marginBottom: 12, textAlign: "center" },
  graphWrapper: { position: "relative" },
  graph: { height: 420, border: "1px solid #e0e0e0", borderRadius: 12, background: "#fbfbff" },
  legend: { display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center", marginTop: 14 },
  legendItem: { display: "flex", alignItems: "center", gap: 6, fontSize: 14, color: "#555" },
  legendDot: { width: 12, height: 12, borderRadius: "50%", display: "inline-block" },
};

export default App;