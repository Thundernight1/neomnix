import { useEffect, useState } from "react";
import { useTheme } from "../lib/useTheme";

const FW = ["soc2", "hipaa", "nist", "mhmda"];
const COLOR = (v: number) => `hsl(${v * 1.2},70%,${95 - v * 0.35}%)`;

export default function Crossmap() {
  useTheme();
  const [matrix, setMatrix] = useState<Record<string, Record<string, number>> | null>(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem("token");

  useEffect(() => {
    fetch("/api/crossmap/matrix", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setMatrix)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "2rem", maxWidth: 700, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Framework Cross-Map</h1>
      <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>
        İki framework arasındaki kontrol örtüşme yüzdesi. Yeşil = yüksek, Kırmızı = düşük.
      </p>
      {loading ? <p style={{ color: "#6b7280" }}>Yükleniyor…</p> : matrix ? (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead><tr>
            <th style={{ padding: "0.5rem 1rem", textAlign: "left" }}></th>
            {FW.map(f => <th key={f} style={{ padding: "0.5rem", fontWeight: 700, textTransform: "uppercase", fontSize: "0.8rem", textAlign: "center" }}>{f}</th>)}
          </tr></thead>
          <tbody>
            {FW.map(row => (
              <tr key={row}>
                <td style={{ padding: "0.5rem 1rem", fontWeight: 700, textTransform: "uppercase", fontSize: "0.8rem" }}>{row}</td>
                {FW.map(col => {
                  const v = matrix?.[row]?.[col] ?? 0;
                  return <td key={col} style={{ padding: "0.75rem", textAlign: "center", background: COLOR(v), border: "1px solid #e5e7eb", fontWeight: 600, borderRadius: 4 }}>{v}%</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p style={{ color: "#ef4444" }}>Veri alınamadı.</p>}
    </div>
  );
}
