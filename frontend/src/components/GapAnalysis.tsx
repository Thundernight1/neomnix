import { useEffect, useState } from "react";
import { useTheme } from "../lib/useTheme";

const P_COLOR: Record<string, string> = { HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#22c55e" };

export default function GapAnalysis() {
  useTheme();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = localStorage.getItem("token");

  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const startAnalysis = async () => {
    setLoading(true); setError(null); setReport(null);
    try {
      const res = await fetch("/api/gap/analyze", {
        method: "POST",
        headers,
        body: JSON.stringify({ org_id: "demo-org", completed_ucl_ids: [], include_ai_recommendations: true }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTaskId(data.task_id);
    } catch { setError("Analiz başlatılamadı."); setLoading(false); }
  };

  useEffect(() => {
    if (!taskId) return;
    const iv = setInterval(async () => {
      const res = await fetch(`/api/gap/results/${taskId}`, { headers });
      const data = await res.json();
      if (data.status === "success") { setReport(data.data); setLoading(false); clearInterval(iv); }
      else if (data.status === "failed") { setError("Analiz başarısız."); setLoading(false); clearInterval(iv); }
    }, 2000);
    return () => clearInterval(iv);
  }, [taskId]);

  return (
    <div style={{ padding: "2rem", maxWidth: 900, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Gap Analizi</h1>
      <p style={{ color: "#6b7280", marginBottom: "1rem" }}>UCL 50 kontrol kataloguyla karşılaştırma.</p>
      <button onClick={startAnalysis} disabled={loading}
        style={{ background: "#01696f", color: "#fff", border: "none", padding: "0.6rem 1.4rem", borderRadius: 6, cursor: "pointer", opacity: loading ? 0.6 : 1 }}>
        {loading ? "Analiz ediliyor…" : "Analizi Başlat"}
      </button>
      {error && <p style={{ color: "#ef4444", marginTop: "1rem" }}>{error}</p>}
      {report && (
        <div style={{ marginTop: "2rem" }}>
          <div style={{ display: "flex", gap: "1.5rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
            {[
              { label: "Skor", value: `${report.score}%`, color: report.score > 70 ? "#22c55e" : "#ef4444" },
              { label: "Toplam", value: report.total_controls },
              { label: "Geçen", value: report.passing_controls, color: "#22c55e" },
              { label: "Eksik", value: report.failing_controls, color: "#ef4444" },
            ].map(s => (
              <div key={s.label} style={{ background: "#f9f8f5", border: "1px solid #e5e7eb", borderRadius: 8, padding: "1rem 1.5rem", minWidth: 120 }}>
                <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>{s.label}</div>
                <div style={{ fontSize: "1.8rem", fontWeight: 700, color: s.color || "#1f2937" }}>{s.value}</div>
              </div>
            ))}
          </div>
          {report.gaps.length === 0
            ? <p style={{ color: "#22c55e", fontWeight: 600 }}>🎉 Tüm kontroller tamamlanmış!</p>
            : report.gaps.map((gap: any) => (
              <div key={gap.ucl_id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: "1rem", marginBottom: "0.75rem", background: "#fff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <b>{gap.ucl_id}</b> — {gap.title}
                    <div style={{ marginTop: 4 }}>{gap.affected_frameworks.map((f: string) =>
                      <span key={f} style={{ background: "#e0f2fe", color: "#0369a1", padding: "2px 8px", borderRadius: 99, marginRight: 4, fontSize: "0.8rem" }}>{f.toUpperCase()}</span>
                    )}</div>
                  </div>
                  <span style={{ background: P_COLOR[gap.priority_level] + "22", color: P_COLOR[gap.priority_level], padding: "2px 10px", borderRadius: 99, fontWeight: 600, fontSize: "0.8rem" }}>
                    {gap.priority_level}
                  </span>
                </div>
                {gap.recommendation && (
                  <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#f0fdf4", borderRadius: 6, fontSize: "0.85rem" }}>
                    <b>🤖 AI Önerisi</b><br/>
                    <b>Neden kritik:</b> {gap.recommendation.why_critical}<br/>
                    <b>Adımlar:</b>
                    <ol style={{ paddingLeft: "1.2rem", margin: "4px 0" }}>
                      {(gap.recommendation.fix_steps || []).map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ol>
                    <b>Tahmini süre:</b> {gap.recommendation.estimated_days} gün<br/>
                    <b>Gerekli kanıt:</b> {gap.recommendation.evidence_needed}<br/>
                    <b>Hibe etkisi:</b> {gap.recommendation.grant_impact}
                  </div>
                )}
              </div>
            ))
          }
        </div>
      )}
    </div>
  );
}
