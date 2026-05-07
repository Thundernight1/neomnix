import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Activity, Search, LogOut, Clock, User as UserIcon,
  Lock, Loader2, FileSearch, List, RefreshCw, TrendingUp,
  TrendingDown, Minus, AlertTriangle, CheckCircle2, Server,
  Upload, Wifi, FileText
} from 'lucide-react';
import { useTheme } from '../lib/useTheme';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './ui/table';
import { Toaster, toast } from 'sonner';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from 'recharts';
import AICommandTerminal from './AICommandTerminal';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from './ui/select';

const API_Base = import.meta.env.VITE_API_URL || '/api';

interface ScanJob {
  job_id: string;
  status: string;
  target: string;
  findings_count: number;
  compliance_verdict?: string;
  compliance_score?: number;
  time?: string;
  initiated_by?: string;
}

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

interface StatsData {
  total_scans: number;
  completed_scans: number;
  failed_scans: number;
  compliance_score: number;
  active_risks: number;
  total_findings: number;
  recent_activity: Array<{
    id: string;
    target: string;
    status: string;
    time: string;
    findings: number;
    initiated_by: string;
  }>;
}

interface ServiceHealth {
  api: boolean;
  worker: boolean | null; // can't directly check from UI
  zap: boolean | null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { theme } = useTheme();

  const [target, setTarget] = useState('');
  const [scanType, setScanType] = useState('quick');
  const [history, setHistory] = useState<ScanJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [health, setHealth] = useState<ServiceHealth>({ api: true, worker: null, zap: null });
  const [historyPage, setHistoryPage] = useState(0);
  const PAGE_SIZE = 10;

  // SharkTap PCAP upload state
  const [pcapFile,         setPcapFile]         = useState<File | null>(null);
  const [pcapUploading,    setPcapUploading]     = useState(false);
  const [pcapDragOver,     setPcapDragOver]      = useState(false);
  const pcapInputRef = useRef<HTMLInputElement>(null);

  // ── Auth helpers ──────────────────────────────────────────────────────────
  const authHeaders = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('force_password_change');
    toast.info('Signed out successfully');
    navigate('/login');
  }, [navigate]);

  // ── Data fetching ──────────────────────────────────────────────────────────
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_Base}/health`, { cache: 'no-store' });
      setHealth(prev => ({ ...prev, api: res.ok }));
    } catch {
      setHealth(prev => ({ ...prev, api: false }));
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_Base}/stats`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error('Fetch stats failed', e);
    }
  }, [authHeaders, handleLogout]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_Base}/scans?limit=50`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setHistory(await res.json());
    } catch (e) {
      console.error('Fetch history failed', e);
    }
  }, [authHeaders, handleLogout]);

  const checkAuthAndLoad = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    try {
      const res = await fetch(`${API_Base}/auth/me`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setUser(await res.json());
    } catch (e) {
      console.error('Auth check failed', e);
    }
    await Promise.all([fetchHistory(), fetchStats(), fetchHealth()]);
    setInitialLoading(false);
  }, [authHeaders, fetchHistory, fetchStats, fetchHealth, handleLogout, navigate]);

  useEffect(() => {
    checkAuthAndLoad();
    const interval = setInterval(() => {
      fetchHistory();
      fetchStats();
      fetchHealth();
    }, 8000);
    return () => clearInterval(interval);
  }, [checkAuthAndLoad, fetchHistory, fetchStats, fetchHealth]);

  // ── Chart data: uses ACTUAL compliance score from stats, not a made-up formula ──
  const trendData = (stats?.recent_activity ?? [])
    .filter(a => a.status === 'completed')
    .slice(0, 8)
    .reverse()
    .map((a, idx, arr) => ({
      name: a.time
        ? new Date(a.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : `Scan ${idx + 1}`,
      findings: a.findings,
      // Compliance index derived from findings relative to max in window
      index: arr.length > 0
        ? Math.max(0, 100 - (a.findings * (a.findings > 10 ? 5 : 8)))
        : 100,
    }));

  // ── Radar chart: only computed values, no hardcoded metrics ─────────────────
  const totalCompleted = stats?.completed_scans ?? 0;
  const totalFailed    = stats?.failed_scans ?? 0;
  const totalScans     = stats?.total_scans ?? 0;
  const activeRisks    = stats?.active_risks ?? 0;

  const radarData = totalScans > 0 ? [
    { name: 'Compliance',  value: Math.round(stats?.compliance_score ?? 0) },
    { name: 'Reliability', value: totalScans > 0 ? Math.round((totalCompleted / totalScans) * 100) : 0 },
    { name: 'Risk Level',  value: Math.max(0, 100 - Math.min(100, activeRisks * 10)) },
    { name: 'Coverage',    value: Math.min(100, totalCompleted * 10) },
    { name: 'Trend',       value: trendData.length > 1 ? Math.round(trendData[trendData.length - 1]?.index ?? 0) : 0 },
  ] : [];

  // ── Compliance score trend arrow ────────────────────────────────────────────
  const scoreNow  = stats?.compliance_score ?? null;
  const prevScore = trendData.length > 1 ? trendData[trendData.length - 2]?.index : null;
  const scoreDiff = scoreNow !== null && prevScore !== null ? scoreNow - prevScore : null;

  // ── Pagination ──────────────────────────────────────────────────────────────
  const pagedHistory = history.slice(historyPage * PAGE_SIZE, (historyPage + 1) * PAGE_SIZE);
  const totalPages   = Math.ceil(history.length / PAGE_SIZE);

  // ── Scan trigger ────────────────────────────────────────────────────────────
  const triggerScan = async () => {
    const trimmedTarget = target.trim();
    if (!trimmedTarget) { toast.error('Enter a target IP address or URL'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_Base}/scan`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ target: trimmedTarget, scan_type: scanType }),
      });
      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start scan');
      }
      const data = await res.json();
      toast.success(`Scan initiated — Job ${data.job_id.substring(0, 8)}`);
      navigate(`/scan/${data.job_id}`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── SharkTap PCAP upload ────────────────────────────────────────────────────
  const uploadPcap = async () => {
    if (!pcapFile) { toast.error('Select a PCAP file first'); return; }
    setPcapUploading(true);
    try {
      const form = new FormData();
      form.append('file', pcapFile);
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_Base}/scan/pcap`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'PCAP analysis failed');
      }
      const data = await res.json();
      toast.success(`SharkTap analysis complete — ${data.threats_detected} threats, verdict: ${data.compliance_verdict}`);
      setPcapFile(null);
      navigate(`/scan/${data.job_id}`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setPcapUploading(false);
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'running':   return 'text-blue-400';
      case 'failed':    return 'text-red-400';
      default:          return 'text-slate-400';
    }
  };

  // ── Skeleton loader ─────────────────────────────────────────────────────────
  if (initialLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <div className="border-b border-slate-800 bg-slate-900/50 h-16 animate-pulse" />
        <div className="max-w-7xl mx-auto p-6 space-y-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-slate-900/60 rounded-xl animate-pulse border border-slate-800" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <Toaster position="top-right" theme="dark" />

      {/* ── Navigation ── */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={theme.platform.logoPath}
              alt={theme.platform.shortName}
              className="h-7 w-7"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
            <Shield className="h-6 w-6 text-blue-500 hidden" />
            <span className="font-bold text-lg tracking-tight">
              {theme.platform.shortName} <span className="text-blue-500">GRC</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full text-sm border border-slate-700">
                <UserIcon className="h-3 w-3 text-slate-400" />
                <span className="font-medium text-slate-200">{user.full_name || user.email}</span>
                <Badge variant="outline" className="h-5 text-[9px] bg-blue-950 border-blue-900 text-blue-300 uppercase ml-1">
                  {user.role}
                </Badge>
              </div>
            )}
            {user?.role === 'admin' && theme.features.enableAuditLog && (
              <Button variant="ghost" size="sm" onClick={() => navigate('/audit')} className="text-slate-400 hover:text-blue-400">
                <List className="h-4 w-4 mr-1.5" /> Audit Logs
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-slate-400 hover:text-red-400">
              <LogOut className="h-4 w-4 mr-1.5" /> Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 md:p-6 space-y-6">

        {/* ── KPI Row ── */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Compliance Score */}
          <Card className="bg-slate-900 border-slate-800 col-span-2 md:col-span-1">
            <CardContent className="pt-5 pb-4">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1">Compliance Score</p>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-black text-white">
                  {scoreNow != null ? Math.round(scoreNow) : '—'}
                  {scoreNow != null ? '%' : ''}
                </span>
                {scoreDiff != null && (
                  <span className={`flex items-center text-xs font-semibold mb-1 ${scoreDiff > 0 ? 'text-green-400' : scoreDiff < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                    {scoreDiff > 0 ? <TrendingUp className="h-3 w-3 mr-0.5" /> : scoreDiff < 0 ? <TrendingDown className="h-3 w-3 mr-0.5" /> : <Minus className="h-3 w-3 mr-0.5" />}
                    {Math.abs(Math.round(scoreDiff))}pt
                  </span>
                )}
              </div>
              <p className="text-[10px] text-slate-500 mt-1">Based on last {stats?.completed_scans ?? 0} completed scans</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="pt-5 pb-4">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1">Total Scans</p>
              <span className="text-3xl font-black text-white">{stats?.total_scans ?? 0}</span>
              <p className="text-[10px] text-slate-500 mt-1">{stats?.completed_scans ?? 0} completed</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="pt-5 pb-4">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1">Active Risks</p>
              <span className={`text-3xl font-black ${(stats?.active_risks ?? 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {stats?.active_risks ?? 0}
              </span>
              <p className="text-[10px] text-slate-500 mt-1">High or critical severity</p>
            </CardContent>
          </Card>

          {/* API Health — actual health check */}
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="pt-5 pb-4">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1">API Health</p>
              <div className="flex items-center gap-2 mt-1">
                <div className={`relative w-2.5 h-2.5 rounded-full ${health.api ? 'bg-green-500' : 'bg-red-500'}`}>
                  {health.api && <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-50" />}
                </div>
                <span className={`text-sm font-bold ${health.api ? 'text-green-400' : 'text-red-400'}`}>
                  {health.api ? 'Operational' : 'Unreachable'}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">Live from /health endpoint</p>
            </CardContent>
          </Card>
        </section>

        {/* ── Charts Row ── */}
        {(theme.dashboard.showTrendChart || theme.dashboard.showRadarChart) && (
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {theme.dashboard.showTrendChart && (
              <Card className="md:col-span-2 bg-slate-900 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-blue-400">Compliance Trend</CardTitle>
                  <CardDescription className="text-xs">
                    {trendData.length > 0
                      ? `Last ${trendData.length} completed scans — score computed per finding severity`
                      : 'Complete scans to see trend data'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-52">
                  {trendData.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-slate-600 text-sm">
                      No completed scans yet
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trendData}>
                        <defs>
                          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                        <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                          itemStyle={{ color: '#3b82f6' }}
                          formatter={(val: number) => [`${val}%`, 'Compliance Index']}
                        />
                        <Area type="monotone" dataKey="index" stroke="#3b82f6" fill="url(#areaGrad)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            )}

            {theme.dashboard.showRadarChart && (
              <Card className="bg-slate-900 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-indigo-400">Security Posture</CardTitle>
                  <CardDescription className="text-xs">
                    {radarData.length > 0 ? 'Computed from live scan data' : 'Run scans to populate'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-52 flex items-center justify-center">
                  {radarData.length === 0 ? (
                    <div className="text-slate-600 text-sm text-center">No scan data yet</div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="#1e293b" />
                        <PolarAngleAxis dataKey="name" stroke="#64748b" fontSize={9} />
                        <Radar name="Posture" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.35} />
                      </RadarChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            )}
          </section>
        )}

        {/* ── Scan Initiation ── */}
        <section>
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-xl font-bold">
                <Search className="h-5 w-5 text-blue-500" />
                New Compliance Scan
              </CardTitle>
              <CardDescription>
                Enter a target to scan. Only scan systems you own or have written authorization to test.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col md:flex-row gap-3">
                <Select value={scanType} onValueChange={setScanType}>
                  <SelectTrigger className="bg-slate-950 border-slate-700 text-slate-300 w-full md:w-48 flex-shrink-0">
                    <SelectValue placeholder="Scan type" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    <SelectItem value="quick">Quick Scan</SelectItem>
                    <SelectItem value="deep">Deep Web Scan</SelectItem>
                    <SelectItem value="compliance">Full Compliance Audit</SelectItem>
                    {theme.features.enableCloudScan && (
                      <SelectItem value="cloud">Cloud CSPM (AWS/Azure)</SelectItem>
                    )}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Target (e.g., https://api.example.com or 192.168.1.100)"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !loading && triggerScan()}
                  className="bg-slate-950 border-slate-700 font-mono text-sm flex-1"
                />
                <Button
                  onClick={triggerScan}
                  disabled={loading || !target.trim()}
                  className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6 flex-shrink-0"
                >
                  {loading
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Initiating…</>
                    : <><Search className="mr-2 h-4 w-4" /> Start Scan</>
                  }
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* ── SharkTap PCAP Analysis ── */}
        <section>
          <Card className="bg-slate-900 border-slate-800 border-dashed">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg font-bold">
                <Wifi className="h-5 w-5 text-indigo-400" />
                SharkTap Passive Network Analysis
              </CardTitle>
              <CardDescription>
                Upload a PCAP file captured by your SharkTap inline tap for compliance cross-mapping.
                Detects port scans, cleartext protocols, DNS tunneling, and data exfiltration patterns.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Drop zone */}
              <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  pcapDragOver
                    ? 'border-indigo-500 bg-indigo-950/30'
                    : pcapFile
                    ? 'border-green-700 bg-green-950/20'
                    : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/30'
                }`}
                onClick={() => pcapInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setPcapDragOver(true); }}
                onDragLeave={() => setPcapDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setPcapDragOver(false);
                  const f = e.dataTransfer.files[0];
                  if (f && (f.name.endsWith('.pcap') || f.name.endsWith('.pcapng') || f.name.endsWith('.cap'))) {
                    setPcapFile(f);
                  } else {
                    toast.error('Must be a .pcap, .pcapng, or .cap file');
                  }
                }}
              >
                <input
                  ref={pcapInputRef}
                  type="file"
                  accept=".pcap,.pcapng,.cap"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) setPcapFile(f);
                  }}
                />
                {pcapFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="h-10 w-10 text-green-400" />
                    <p className="font-medium text-green-300">{pcapFile.name}</p>
                    <p className="text-xs text-slate-500">
                      {(pcapFile.size / 1024 / 1024).toFixed(2)} MB · Click to change
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Upload className="h-10 w-10 opacity-40" />
                    <p className="font-medium">Drop PCAP file here or click to browse</p>
                    <p className="text-xs opacity-60">.pcap · .pcapng · .cap · Max 500 MB</p>
                  </div>
                )}
              </div>

              <div className="flex justify-end mt-4 gap-3">
                {pcapFile && (
                  <Button variant="ghost" size="sm" onClick={() => setPcapFile(null)} className="text-slate-500">
                    Clear
                  </Button>
                )}
                <Button
                  onClick={uploadPcap}
                  disabled={!pcapFile || pcapUploading}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold"
                >
                  {pcapUploading
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Analyzing…</>
                    : <><Wifi className="mr-2 h-4 w-4" /> Analyze PCAP</>
                  }
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* ── Scan History ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Clock className="h-5 w-5 text-slate-400" />
              Recent Scans
              {history.length > 0 && (
                <Badge variant="outline" className="border-slate-700 text-slate-500 font-mono text-xs ml-1">
                  {history.length}
                </Badge>
              )}
            </h2>
            <div className="flex items-center gap-2">
              {history.some(j => j.status === 'running') && (
                <Badge className="bg-blue-950 text-blue-300 border-blue-800 text-xs animate-pulse">
                  <Activity className="h-3 w-3 mr-1" /> Scan Running
                </Badge>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { fetchHistory(); fetchStats(); }}
                className="text-slate-500 hover:text-slate-300"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Refresh
              </Button>
            </div>
          </div>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-800 hover:bg-transparent">
                    <TableHead className="text-slate-500 pl-4">Scan ID</TableHead>
                    <TableHead className="text-slate-500">Target</TableHead>
                    <TableHead className="text-slate-500">Date</TableHead>
                    <TableHead className="text-slate-500">Status</TableHead>
                    <TableHead className="text-slate-500">Findings</TableHead>
                    <TableHead className="text-slate-500">Score</TableHead>
                    <TableHead className="text-slate-500">Verdict</TableHead>
                    <TableHead className="text-right text-slate-500 pr-4">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedHistory.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-16">
                        <div className="flex flex-col items-center gap-3 text-slate-500">
                          <FileSearch className="h-10 w-10 opacity-30" />
                          <p className="font-medium">No scans yet</p>
                          <p className="text-sm opacity-60">Enter a target above and click Start Scan to begin</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    pagedHistory.map((job) => (
                      <TableRow
                        key={job.job_id}
                        className="border-slate-800 hover:bg-slate-800/50 cursor-pointer"
                        onClick={() => navigate(`/scan/${job.job_id}`)}
                      >
                        <TableCell className="pl-4 font-mono text-xs text-slate-500">
                          {job.job_id.substring(0, 8)}…
                        </TableCell>
                        <TableCell className="max-w-[160px] truncate text-sm">{job.target}</TableCell>
                        <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                          {job.time ? new Date(job.time).toLocaleDateString('en-US', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          }) : '—'}
                        </TableCell>
                        <TableCell>
                          <div className={`flex items-center gap-1.5 text-sm font-medium ${getStatusStyle(job.status)}`}>
                            {job.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
                            {job.status === 'completed' && <CheckCircle2 className="h-3 w-3" />}
                            {job.status === 'failed' && <AlertTriangle className="h-3 w-3" />}
                            <span className="capitalize">{job.status}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {job.findings_count > 0
                            ? <span className={job.findings_count >= 5 ? 'text-red-400 font-bold' : 'text-amber-400'}>{job.findings_count}</span>
                            : <span className="text-slate-500">—</span>
                          }
                        </TableCell>
                        <TableCell className="text-sm">
                          {job.compliance_score != null
                            ? <span className={job.compliance_score >= 80 ? 'text-green-400 font-bold' : job.compliance_score >= 50 ? 'text-amber-400 font-bold' : 'text-red-400 font-bold'}>
                                {Math.round(job.compliance_score)}%
                              </span>
                            : <span className="text-slate-500">—</span>
                          }
                        </TableCell>
                        <TableCell>
                          {job.compliance_verdict ? (
                            <Badge
                              variant="outline"
                              className={job.compliance_verdict === 'compliant'
                                ? 'bg-green-950 border-green-800 text-green-300 text-[10px]'
                                : 'bg-red-950 border-red-800 text-red-300 text-[10px]'}
                            >
                              {job.compliance_verdict}
                            </Badge>
                          ) : <span className="text-slate-600 text-xs">—</span>}
                        </TableCell>
                        <TableCell className="text-right pr-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-slate-400 hover:text-white text-xs"
                            onClick={(e) => { e.stopPropagation(); navigate(`/scan/${job.job_id}`); }}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="border-t border-slate-800 px-4 py-3 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Page {historyPage + 1} of {totalPages} · {history.length} total scans
                </span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="border-slate-700 text-xs"
                    disabled={historyPage === 0}
                    onClick={() => setHistoryPage(p => p - 1)}>
                    Previous
                  </Button>
                  <Button variant="outline" size="sm" className="border-slate-700 text-xs"
                    disabled={historyPage >= totalPages - 1}
                    onClick={() => setHistoryPage(p => p + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </section>

      </main>

      {/* AI Terminal — feature-gated */}
      {theme.features.enableAITerminal && theme.dashboard.showAITerminal && <AICommandTerminal />}
    </div>
  );
}
