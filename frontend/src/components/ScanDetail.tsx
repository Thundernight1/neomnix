import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Shield, AlertTriangle, CheckCircle, Loader2, Search,
  Cpu, Zap, Download, ArrowLeft, Clock, RefreshCw, XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { toast } from 'sonner';
import { Toaster } from './ui/sonner';
import { motion } from 'framer-motion';

const API_Base = import.meta.env.VITE_API_URL || '/api';

interface Finding {
  id?: string;
  severity: string;
  description: string;
  evidence?: string;
  remediation?: string;
  control?: string;
  framework?: string;
}

interface ScanDetailData {
  job_id: string;
  status: string;
  target: string;
  findings_count: number;
  compliance_verdict?: string;
  compliance_score?: number;
  details?: {
    findings?: Finding[];
    mapped_controls?: string[];
    unmapped_findings?: string[];
    determination?: string;
  };
}

// Scan phases — honest representation of what each phase means
const SCAN_PHASES = [
  { name: 'Enumeration',        icon: Search, color: 'text-blue-400',   description: 'Port & service discovery' },
  { name: 'Vulnerability Scan', icon: Cpu,    color: 'text-indigo-400', description: 'ZAP active scan' },
  { name: 'Compliance Mapping', icon: Zap,    color: 'text-amber-400',  description: 'Control framework mapping' },
  { name: 'Report Generation',  icon: Shield, color: 'text-green-400',  description: 'Executive report' },
];

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'];

function getSeverityStyle(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical': return 'text-red-400 bg-red-950/30 border-red-800';
    case 'high':     return 'text-orange-400 bg-orange-950/30 border-orange-800';
    case 'medium':   return 'text-yellow-400 bg-yellow-950/30 border-yellow-800';
    default:         return 'text-blue-400 bg-blue-950/30 border-blue-800';
  }
}

function getSeverityBadgeStyle(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical': return 'bg-red-900 text-red-300 border-red-800';
    case 'high':     return 'bg-orange-900 text-orange-300 border-orange-800';
    case 'medium':   return 'bg-yellow-900 text-yellow-300 border-yellow-800';
    default:         return 'bg-blue-900 text-blue-300 border-blue-800';
  }
}

export default function ScanDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const getToken = () => localStorage.getItem('token') || localStorage.getItem('isAuthenticated');

  const fetchScanDetails = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const token = getToken();
      if (!token) { navigate('/login'); return; }

      const res = await fetch(`${API_Base}/scan/${id}`, {
        credentials: 'include',
      });

      if (res.status === 401) { navigate('/login'); return; }
      if (res.status === 404) { setError('Scan not found. It may have been deleted.'); return; }
      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data: ScanDetailData = await res.json();
      setScan(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load scan details.');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchScanDetails();
    const poll = setInterval(() => {
      // Only keep polling while the scan is actively running
      setScan(prev => {
        if (prev && (prev.status === 'running' || prev.status === 'pending')) {
          fetchScanDetails(true);
        }
        return prev;
      });
    }, 8000);
    return () => clearInterval(poll);
  }, [fetchScanDetails]);

  // ── PDF Download ────────────────────────────────────────────────────────────
  const downloadReport = async (framework: string) => {
    setDownloading(framework);
    let objectUrl: string | null = null;
    try {
      const token = getToken();
      const res = await fetch(`${API_Base}/reports/pdf/${id}/${framework}`, {
        credentials: 'include',
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || 'Download failed');
      }

      const blob = await res.blob();
      objectUrl = window.URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = objectUrl;
      a.download = `${framework}_report_${id?.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      // Revoke after a short delay to ensure download starts
      setTimeout(() => { if (objectUrl) window.URL.revokeObjectURL(objectUrl); }, 2000);
      toast.success(`${framework} report downloaded`);
    } catch (err: any) {
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
      toast.error(`Failed to download ${framework} report: ${err.message}`);
    } finally {
      setDownloading(null);
    }
  };

  // ── Phase inference from status ─────────────────────────────────────────────
  const getCurrentPhase = () => {
    if (!scan) return -1;
    if (scan.status === 'completed') return 3;
    if (scan.status === 'failed') return -1;
    if (scan.status === 'pending') return 0;
    // 'running' — infer phase from findings count as a rough proxy
    const f = scan.findings_count || 0;
    if (f === 0) return 0;
    if (f < 5) return 1;
    if (f < 10) return 2;
    return 3;
  };

  const currentPhase = getCurrentPhase();

  // ── Sorted findings by severity ─────────────────────────────────────────────
  const sortedFindings = [...(scan?.details?.findings ?? [])].sort((a, b) => {
    return SEVERITY_ORDER.indexOf(a.severity.toLowerCase()) - SEVERITY_ORDER.indexOf(b.severity.toLowerCase());
  });

  const criticalCount = sortedFindings.filter(f => f.severity.toLowerCase() === 'critical').length;
  const highCount     = sortedFindings.filter(f => f.severity.toLowerCase() === 'high').length;
  const mediumCount   = sortedFindings.filter(f => f.severity.toLowerCase() === 'medium').length;
  const lowCount      = sortedFindings.filter(f => f.severity.toLowerCase() === 'low').length;

  // ── Loading / Error states ──────────────────────────────────────────────────
  if (loading && !scan) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="flex flex-col items-center gap-4 text-slate-400">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
          <p className="text-sm">Loading scan details…</p>
        </div>
      </div>
    );
  }

  if (error && !scan) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950 p-6">
        <Card className="bg-slate-900 border-red-900 max-w-md w-full text-center">
          <CardContent className="pt-10 pb-8 flex flex-col items-center gap-4">
            <XCircle className="w-12 h-12 text-red-500" />
            <p className="text-red-300 font-medium">{error}</p>
            <Button variant="outline" onClick={() => navigate('/')} className="border-slate-700 text-slate-300">
              <ArrowLeft className="h-4 w-4 mr-2" /> Return to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!scan) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <Toaster position="top-right" theme="dark" />

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/')} className="text-slate-400 hover:text-white">
              <ArrowLeft className="h-4 w-4 mr-2" /> Dashboard
            </Button>
            <div className="h-4 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              <span className="font-bold">Scan Report</span>
            </div>
            <Badge variant="outline" className="font-mono text-[10px] text-slate-500 border-slate-700">
              {scan.job_id.substring(0, 12)}…
            </Badge>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-[11px] text-slate-600 flex items-center gap-1">
                <Clock className="h-3 w-3" /> Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => fetchScanDetails()} className="text-slate-500 hover:text-slate-300">
              <RefreshCw className="h-3 w-3 mr-1" /> Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">

        {/* Scan Phase Progress */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {SCAN_PHASES.map((phase, idx) => {
            const isDone    = idx < currentPhase || scan.status === 'completed';
            const isActive  = idx === currentPhase && scan.status === 'running';
            const isPending = idx > currentPhase && scan.status !== 'completed';
            const isFailed  = scan.status === 'failed';

            return (
              <div
                key={phase.name}
                className={`relative flex flex-col items-center p-4 rounded-xl border transition-all duration-300 ${
                  isFailed
                    ? 'bg-red-950/20 border-red-900/50 opacity-60'
                    : isDone
                    ? 'bg-slate-900 border-blue-600/40 shadow-md shadow-blue-900/10'
                    : isActive
                    ? 'bg-slate-900 border-blue-500/60 shadow-lg shadow-blue-900/20'
                    : isPending
                    ? 'bg-slate-950 border-slate-800 opacity-40'
                    : 'bg-slate-900 border-slate-800'
                }`}
              >
                <phase.icon className={`h-5 w-5 mb-2 ${isDone || isActive ? phase.color : 'text-slate-600'}`} />
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">{phase.name}</span>
                <span className="text-[9px] text-slate-600 mt-0.5 text-center leading-tight">{phase.description}</span>
                {isDone && <CheckCircle className="absolute top-2 right-2 h-3 w-3 text-green-500" />}
                {isActive && <Loader2 className="absolute top-2 right-2 h-3 w-3 text-blue-500 animate-spin" />}
              </div>
            );
          })}
        </div>

        {/* Status + Score Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Scan Metadata */}
          <Card className="lg:col-span-2 bg-slate-900 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                <Shield className="h-4 w-4" /> Scan Details
              </CardTitle>
              {scan.status === 'completed' && (
                <div className="flex flex-wrap gap-2">
                  {(['HIPAA-2026', 'SOC2', 'NIST-800-53'] as const).map((fw) => (
                    <Button
                      key={fw}
                      size="sm"
                      variant="outline"
                      className="h-7 text-[10px] border-slate-700 hover:border-blue-600"
                      onClick={() => downloadReport(fw)}
                      disabled={!!downloading}
                    >
                      {downloading === fw
                        ? <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        : <Download className="h-3 w-3 mr-1" />
                      }
                      {fw}
                    </Button>
                  ))}
                </div>
              )}
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Target</div>
                <div className="font-mono text-sm text-blue-200 break-all">{scan.target}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Status</div>
                <Badge
                  variant="outline"
                  className={`uppercase text-[10px] ${
                    scan.status === 'completed' ? 'bg-green-950 border-green-800 text-green-300'
                    : scan.status === 'running'  ? 'bg-blue-950 border-blue-800 text-blue-300 animate-pulse'
                    : scan.status === 'failed'   ? 'bg-red-950 border-red-800 text-red-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {scan.status === 'running' && <Loader2 className="h-2 w-2 animate-spin mr-1" />}
                  {scan.status}
                </Badge>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Verdict</div>
                <div
                  className={`font-black text-sm tracking-tight ${
                    scan.compliance_verdict === 'compliant' ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {scan.status === 'running' || scan.status === 'pending'
                    ? '—'
                    : (scan.compliance_verdict?.replace(/_/g, ' ').toUpperCase() || 'PENDING')}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Findings</div>
                <div className="flex gap-2 flex-wrap">
                  {criticalCount > 0 && <span className="text-[10px] font-bold text-red-400">{criticalCount} CRIT</span>}
                  {highCount     > 0 && <span className="text-[10px] font-bold text-orange-400">{highCount} HIGH</span>}
                  {mediumCount   > 0 && <span className="text-[10px] font-bold text-yellow-400">{mediumCount} MED</span>}
                  {lowCount      > 0 && <span className="text-[10px] font-bold text-blue-400">{lowCount} LOW</span>}
                  {scan.findings_count === 0 && scan.status === 'completed' && (
                    <span className="text-[10px] font-bold text-green-400">NONE</span>
                  )}
                  {(scan.status === 'running' || scan.status === 'pending') && (
                    <span className="text-[10px] text-slate-500">Scanning…</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Compliance Score Ring */}
          <Card className="bg-slate-900 border-slate-800 flex flex-col items-center justify-center p-6">
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-3 tracking-widest">
              Compliance Score
            </div>
            {scan.status === 'running' || scan.status === 'pending' ? (
              <div className="flex flex-col items-center gap-3 py-4">
                <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
                <p className="text-xs text-slate-500">Computing…</p>
              </div>
            ) : (
              <div className="relative w-36 h-36">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
                  <circle cx="80" cy="80" r="68" fill="transparent" stroke="#1e293b" strokeWidth="10" />
                  <motion.circle
                    cx="80" cy="80" r="68"
                    fill="transparent"
                    stroke={
                      (scan.compliance_score ?? 0) >= 80 ? '#22c55e'
                      : (scan.compliance_score ?? 0) >= 50 ? '#f59e0b'
                      : '#ef4444'
                    }
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 68}`}
                    initial={{ strokeDashoffset: 2 * Math.PI * 68 }}
                    animate={{
                      strokeDashoffset:
                        2 * Math.PI * 68 * (1 - (scan.compliance_score ?? 0) / 100),
                    }}
                    transition={{ duration: 1.2, ease: 'easeOut' }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-black text-white">
                    {scan.compliance_score != null ? Math.round(scan.compliance_score) : '—'}
                    {scan.compliance_score != null ? '%' : ''}
                  </span>
                  <span className="text-[9px] text-slate-500 uppercase tracking-widest mt-1">
                    {scan.status === 'completed' ? 'Verified' : '—'}
                  </span>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Running state notice */}
        {(scan.status === 'running' || scan.status === 'pending') && (
          <Alert className="bg-blue-950/30 border-blue-800 text-blue-200">
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertTitle className="text-blue-300 font-semibold">Scan In Progress</AlertTitle>
            <AlertDescription className="text-blue-400/80 text-sm">
              The scan engine is actively analyzing <span className="font-mono font-bold">{scan.target}</span>.
              This page polls automatically every 8 seconds. Results will appear when the scan completes.
            </AlertDescription>
          </Alert>
        )}

        {scan.status === 'failed' && (
          <Alert className="bg-red-950/30 border-red-800 text-red-200">
            <XCircle className="h-4 w-4" />
            <AlertTitle className="text-red-300 font-semibold">Scan Failed</AlertTitle>
            <AlertDescription className="text-red-400/80 text-sm">
              The scan could not be completed. This may be due to an unreachable target, a network timeout, or an
              internal worker error. Check the system logs for details, then retry from the dashboard.
            </AlertDescription>
          </Alert>
        )}

        {/* Findings List */}
        {scan.status === 'completed' && (
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                Detailed Findings
                <Badge variant="outline" className="ml-2 border-slate-700 text-slate-400 font-mono text-xs">
                  {sortedFindings.length} total
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {sortedFindings.length === 0 ? (
                <div className="text-center py-16 space-y-3">
                  <CheckCircle className="mx-auto h-14 w-14 text-green-500/30" />
                  <p className="text-green-400 font-semibold">No Findings Detected</p>
                  <p className="text-slate-500 text-sm">The scan completed without identifying any compliance gaps.</p>
                </div>
              ) : (
                <ScrollArea className="max-h-[700px] pr-2">
                  <div className="space-y-3">
                    {sortedFindings.map((f, i) => (
                      <Alert key={f.id ?? i} className={`border ${getSeverityStyle(f.severity)}`}>
                        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                        <AlertTitle className="flex items-center gap-2 font-semibold text-xs uppercase tracking-wide">
                          <Badge variant="outline" className={`text-[9px] uppercase ${getSeverityBadgeStyle(f.severity)}`}>
                            {f.severity}
                          </Badge>
                          {f.control && (
                            <span className="font-mono text-[10px] text-slate-500">{f.control}</span>
                          )}
                          {f.framework && (
                            <Badge variant="outline" className="text-[9px] border-slate-700 text-slate-500">{f.framework}</Badge>
                          )}
                        </AlertTitle>
                        <AlertDescription className="mt-2 space-y-2">
                          <p className="text-slate-200 text-sm font-medium">{f.description}</p>
                          {f.evidence && (
                            <pre className="bg-black/40 p-2.5 rounded text-[11px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap break-words">
                              {f.evidence}
                            </pre>
                          )}
                          {f.remediation && (
                            <div className="text-sm text-blue-300 bg-blue-950/20 border border-blue-900/40 rounded p-2">
                              <span className="font-semibold text-blue-400">Remediation: </span>
                              {f.remediation}
                            </div>
                          )}
                        </AlertDescription>
                      </Alert>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        )}

      </main>
    </div>
  );
}
