import { useState } from "react";
import { askQuestion } from "../api/client";

const SAMPLES = [
  "S1 điều khiển đèn nào?",
  "P5 được cấp nguồn bởi đâu?",
  "Tổng công suất đèn là bao nhiêu?",
];

export default function QaBox({ jobId }) {
  const [q, setQ] = useState("");
  const [ans, setAns] = useState(null);
  const [loading, setLoading] = useState(false);

  const ask = async (question) => {
    const text = question ?? q;
    if (!text.trim()) return;
    setQ(text);
    setLoading(true);
    try {
      setAns(await askQuestion(jobId, text));
    } catch (e) {
      setAns({ answer: e.message, found: false });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section">
      <h2>Hỏi đáp (QA — rule-based)</h2>
      <div className="qa-input">
        <input
          value={q}
          placeholder="VD: S1 điều khiển đèn nào?"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button className="btn" onClick={() => ask()} disabled={loading}>
          {loading ? "…" : "Hỏi"}
        </button>
      </div>
      <div className="qa-samples">
        {SAMPLES.map((s) => (
          <span className="chip" key={s} onClick={() => ask(s)}>{s}</span>
        ))}
      </div>
      {ans && (
        <div className="qa-answer" style={{ marginTop: 12 }}>
          {ans.answer}
        </div>
      )}
    </div>
  );
}
