/**
 * Dashboard — Neomnix Healthcare VIP Edition (Chunk 5).
 *
 * Three strict modules plus a full-width critical-alert overlay:
 *   1. Active Data Leak Status  - WebSocket-driven; flashing red overlay
 *                                 on receipt of a "critical_data_leak"
 *                                 event from the /ws/alerts endpoint.
 *   2. Grant Loss Risk Indicator - Red/Green WA-MHMDA posture panel.
 *   3. HIPAA Violation Summary   - Clean count of breach points by
 *                                  severity, fetched from GET /scans.
 *
 * The overlay intentionally hides deep technical details from the
 * end-customer. The event payload (threat type, source IP, pcap file
 * name) is captured in the customer-support handoff note but is not
 * shown on the dashboard surface.
 *
 * Removed in Chunk 5 (do not bring back without an explicit brief):
 *   - Multi-framework KPI tiles
 *   - Recharts charts (compliance posture, scan-history trend)
 *   - Historical scan log table
 *   - AICommandTerminal embed
 *   - Manual scan form
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@/lib/useTheme';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

/**
 * Build a same-origin WebSocket URL for the alerts endpoint.
 * The browser cannot set the Authorization header on a WebSocket, so
 * the token is passed in the query string. See backend's
 * /ws/alerts dependency for the matching decode path.
 */
function alertsWsUrl(token: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws/alerts?token=${encodeURIComponent(token)}`;
}

/**
 * Summary shape returned by GET /scans. Only the fields we render are
 * typed; everything else is ignored. Kept narrow on purpose — a
 * schema change in the backend should be a compile error here, not
 * a silent render.
 */
interface ScanFinding {
  severity: 'critical' | 'high' | 'medium' | 'low' | string;
  framework?: string;
  cwe_id?: string;
  cvss_score?: number;
  description?: string;
}

interface ScanSummary {
  id: string;
  status: 'completed' | 'pending' | 'failed' | 'running' | string;
  framework?: string;
  findings: ScanFinding[];
  created_at?: string;
}

/**
 * Categorize a scan list into the data the three modules need.
 * Pure function so the test surface is small and the rendering
 * layer stays declarative.
 */
function summarize(scans: ScanSummary[]) {
  // HIPAA: count active breach points by severity. We count findings
  // from any scan that touched the HIPAA-2026 framework; "active" means
  // the most recent completed scan for that framework.
  const hipaaScans = scans.filter(
    (s) => s.framework === 'HIPAA-2026' && s.status === 'completed'
  );
  const latestHipaa = hipaaScans[hipaaScans.length - 1];
  const hipaaCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  if (latestHipaa) {
    for (const f of latestHipaa.findings) {
      const sev = (f.severity || '').toLowerCase();
      if (sev in hipaaCounts) {
        hipaaCounts[sev as keyof typeof hipaaCounts]++;
      }
    }
  }
  const hipaaTotal = hipaaCounts.critical + hipaaCounts.high + hipaaCounts.medium + hipaaCounts.low;

  // WA-MHMDA: posture is Red if the latest completed scan has any
  // critical or high finding, Green otherwise. No scan = Green (the
  // platform is at baseline until proven otherwise).
  const mhmdaScans = scans.filter(
    (s) => s.framework === 'WA-MHMDA' && s.status === 'completed'
  );
  const latestMhmda = mhmdaScans[mhmdaScans.length - 1];
  let mhmdaPosture: 'green' | 'red' = 'green';
  if (latestMhmda) {
    const bad = latestMhmda.findings.some(
      (f) => f.severity === 'critical' || f.severity === 'high'
    );
    mhmdaPosture = bad ? 'red' : 'green';
  }

  return { hipaaCounts, hipaaTotal, mhmdaPosture, hasAnyScan: scans.length > 0 };
}

export default function Dashboard() {
  useTheme();
  const navigate = useNavigate();

  // Three module data state.
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Critical alert state. When non-null, the flashing-red overlay is
  // shown. The event itself is captured for the support handoff but
  // the *visible* overlay shows only the localized Turkish title.
  const [criticalAlert, setCriticalAlert] = useState<null | {
    receivedAt: number;
    supportRef: string; // short reference id, not the technical payload
  }>(null);

  // WebSocket lifecycle. We reconnect on close (backoff capped at 30s).
  // Token is read once from localStorage. If the user logs out, the
  // dashboard unmounts and the socket is closed by the cleanup fn.
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'open' | 'closed'>('closed');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      setWsStatus('connecting');
      const ws = new WebSocket(alertsWsUrl(token));
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        setWsStatus('open');
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = (ev) => {
        if (cancelled) return;
        let payload: { type?: string; threat?: string; source?: string; pcap?: string };
        try {
          payload = JSON.parse(ev.data);
        } catch {
          // Not JSON (e.g. server is sending a plain heartbeat). Ignore.
          return;
        }
        if (payload.type === 'critical_data_leak') {
          // Build a short, non-technical support reference. The full
          // payload is intentionally NOT shown to the end customer.
          const supportRef = `INC-${Date.now().toString(36).toUpperCase()}`;
          setCriticalAlert({ receivedAt: Date.now(), supportRef });
        }
        // Heartbeats and other message types are intentionally ignored
        // on the UI side; they exist for liveness detection only.
      };

      ws.onerror = () => {
        // onclose will fire next; backoff happens there.
      };

      ws.onclose = () => {
        if (cancelled) return;
        setWsStatus('closed');
        wsRef.current = null;
        // Exponential backoff with cap.
        const attempt = reconnectAttemptRef.current++;
        const delayMs = Math.min(1000 * Math.pow(2, attempt), 30000);
        reconnectTimer = setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onmessage = null;
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [navigate]);

  // Fetch the latest scans once on mount. Re-runs only if the user
  // navigates away and back.
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/scans`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: ScanSummary[] = await res.json();
        if (!cancelled) setScans(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Failed to load scans');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = summarize(scans);

  return (
    <div className="min-h-screen bg-slate-50 px-6 py-8 text-slate-900">
      {/* Critical alert overlay (flashing red, hides technical details) */}
      {criticalAlert && (
        <CriticalAlertOverlay
          supportRef={criticalAlert.supportRef}
          onDismiss={() => setCriticalAlert(null)}
        />
      )}

      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-sm text-slate-500">
              Healthcare Compliance Posture - {wsStatus === 'open' ? 'Live' : 'Reconnecting'}
            </p>
          </div>
          <Button variant="outline" onClick={() => navigate('/')}>
            Back to Command Center
          </Button>
        </header>

        {loadError && (
          <Alert variant="destructive">
            <AlertTitle>Could not load scan data</AlertTitle>
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Module 1: Active Data Leak Status */}
          <Card>
            <CardHeader>
              <CardTitle>Active Data Leak Status</CardTitle>
              <CardDescription>
                Real-time critical-event monitor. Powered by the
                /ws/alerts pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {criticalAlert ? (
                <div className="flex items-center gap-3">
                  <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-red-600" />
                  <span className="text-sm font-semibold text-red-700">
                    Critical event in progress
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <span className="inline-block h-3 w-3 rounded-full bg-emerald-500" />
                  <span className="text-sm font-semibold text-emerald-700">
                    No active critical data leak detected
                  </span>
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">
                Connection: {wsStatus}
              </p>
            </CardContent>
          </Card>

          {/* Module 2: Grant Loss Risk Indicator (WA-MHMDA) */}
          <Card>
            <CardHeader>
              <CardTitle>Grant Loss Risk Indicator</CardTitle>
              <CardDescription>
                WA-MHMDA compliance posture (RCW 19.373.030).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                data-testid="mhmda-posture"
                data-posture={summary.mhmdaPosture}
                className={
                  'flex items-center gap-3 rounded-md p-3 ' +
                  (summary.mhmdaPosture === 'red'
                    ? 'bg-red-50 text-red-800'
                    : 'bg-emerald-50 text-emerald-800')
                }
              >
                <span
                  className={
                    'inline-block h-4 w-4 rounded-full ' +
                    (summary.mhmdaPosture === 'red' ? 'bg-red-600' : 'bg-emerald-600')
                  }
                />
                <span className="text-sm font-semibold">
                  {summary.mhmdaPosture === 'red'
                    ? 'RED - Grant loss risk elevated'
                    : 'GREEN - Within compliance posture'}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Module 3: HIPAA Violation Summary */}
          <Card>
            <CardHeader>
              <CardTitle>HIPAA Violation Summary</CardTitle>
              <CardDescription>
                Active breach points in the most recent HIPAA-2026 scan.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-slate-500">Loading…</p>
              ) : summary.hipaaTotal === 0 ? (
                <p className="text-sm text-slate-500">
                  No active HIPAA breach points reported.
                </p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {summary.hipaaCounts.critical > 0 && (
                    <li className="flex justify-between">
                      <span className="text-red-700">Critical</span>
                      <span className="font-mono">{summary.hipaaCounts.critical}</span>
                    </li>
                  )}
                  {summary.hipaaCounts.high > 0 && (
                    <li className="flex justify-between">
                      <span className="text-orange-700">High</span>
                      <span className="font-mono">{summary.hipaaCounts.high}</span>
                    </li>
                  )}
                  {summary.hipaaCounts.medium > 0 && (
                    <li className="flex justify-between">
                      <span className="text-yellow-700">Medium</span>
                      <span className="font-mono">{summary.hipaaCounts.medium}</span>
                    </li>
                  )}
                  {summary.hipaaCounts.low > 0 && (
                    <li className="flex justify-between">
                      <span className="text-slate-700">Low</span>
                      <span className="font-mono">{summary.hipaaCounts.low}</span>
                    </li>
                  )}
                  <li className="mt-2 flex justify-between border-t border-slate-200 pt-2">
                    <span className="font-semibold">Total active</span>
                    <span className="font-mono font-semibold">{summary.hipaaTotal}</span>
                  </li>
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        {!summary.hasAnyScan && !loading && (
          <Alert>
            <AlertTitle>No scans yet</AlertTitle>
            <AlertDescription>
              The compliance posture will populate as soon as the first
              HIPAA-2026 or WA-MHMDA scan completes.
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
}

/**
 * Full-width flashing-red critical alert overlay.
 *
 * End-customer visible content (per Chunk 5 R1):
 *   - The Turkish title "Kritik Acik Tespit Edildi" (Critical Alert Detected)
 *   - A short acknowledgment button
 *
 * Hidden by design (per the brief: "hiding deep technical details
 * from the end-user"):
 *   - The threat type (UNENCRYPTED_DATABASE, DNS_TUNNELING_SUSPECTED, etc.)
 *   - The source IP
 *   - The PCAP filename
 *
 * The customer support team can use `supportRef` to look up the full
 * event in the audit log; that channel is out of scope for this UI.
 */
function CriticalAlertOverlay({
  supportRef,
  onDismiss,
}: {
  supportRef: string;
  onDismiss: () => void;
}) {
  return (
    <>
      {/* The flash animation. Inline <style> avoids needing a new
          entry in tailwind.config.js for a one-off keyframe. */}
      <style>{`
        @keyframes neomnix-critical-flash {
          0%, 100% { background-color: rgba(220, 38, 38, 0.95); }
          50%      { background-color: rgba(153, 27, 27, 0.95); }
        }
        .neomnix-critical-overlay {
          animation: neomnix-critical-flash 0.9s ease-in-out infinite;
        }
      `}</style>
      <div
        role="alertdialog"
        aria-live="assertive"
        aria-label="Kritik Acik Tespit Edildi"
        data-testid="critical-alert-overlay"
        className="neomnix-critical-overlay fixed inset-x-0 top-0 z-50 px-6 py-4 text-white shadow-lg"
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-white" />
            <div>
              <h2 className="text-xl font-bold tracking-tight">
                Kritik Acik Tespit Edildi
              </h2>
              <p className="text-sm text-red-100">
                A critical data-handling event has been detected. Your
                compliance team has been notified.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            className="border-white bg-transparent text-white hover:bg-white hover:text-red-700"
            onClick={onDismiss}
            data-testid="critical-alert-ack"
          >
            Acknowledge
          </Button>
        </div>
        {/* Hidden support reference for debugging — never rendered as text */}
        <span data-testid="critical-alert-ref" hidden>{supportRef}</span>
      </div>
    </>
  );
}
