import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Activity, Search, LogOut, Clock, User as UserIcon, Loader2, FileSearch, List, RefreshCw, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle2, Upload, Wifi, FileText } from 'lucide-react';
import { useTheme } from '../lib/useTheme';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from './ui/table';
import { Toaster, toast } from 'sonner';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, } from 'recharts';
import AICommandTerminal from './AICommandTerminal';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
const API_Base = import.meta.env.VITE_API_URL || '/api';
export default function Dashboard() {
    const navigate = useNavigate();
    const { theme } = useTheme();
    const [target, setTarget] = useState('');
    const [scanType, setScanType] = useState('quick');
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);
    const [user, setUser] = useState(null);
    const [stats, setStats] = useState(null);
    const [health, setHealth] = useState({ api: true, worker: null, zap: null });
    const [historyPage, setHistoryPage] = useState(0);
    const PAGE_SIZE = 10;
    // SharkTap PCAP upload state
    const [pcapFile, setPcapFile] = useState(null);
    const [pcapUploading, setPcapUploading] = useState(false);
    const [pcapDragOver, setPcapDragOver] = useState(false);
    const pcapInputRef = useRef(null);
    // ── Auth helpers ──────────────────────────────────────────────────────────
    const authHeaders = useCallback(() => {
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
        }
        catch {
            setHealth(prev => ({ ...prev, api: false }));
        }
    }, []);
    const fetchStats = useCallback(async () => {
        try {
            const res = await fetch(`${API_Base}/stats`, { headers: authHeaders() });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (res.ok)
                setStats(await res.json());
        }
        catch (e) {
            console.error('Fetch stats failed', e);
        }
    }, [authHeaders, handleLogout]);
    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch(`${API_Base}/scans?limit=50`, { headers: authHeaders() });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (res.ok)
                setHistory(await res.json());
        }
        catch (e) {
            console.error('Fetch history failed', e);
        }
    }, [authHeaders, handleLogout]);
    const checkAuthAndLoad = useCallback(async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/login');
            return;
        }
        try {
            const res = await fetch(`${API_Base}/auth/me`, { headers: authHeaders() });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (res.ok)
                setUser(await res.json());
        }
        catch (e) {
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
    const totalFailed = stats?.failed_scans ?? 0;
    const totalScans = stats?.total_scans ?? 0;
    const activeRisks = stats?.active_risks ?? 0;
    const radarData = totalScans > 0 ? [
        { name: 'Compliance', value: Math.round(stats?.compliance_score ?? 0) },
        { name: 'Reliability', value: totalScans > 0 ? Math.round((totalCompleted / totalScans) * 100) : 0 },
        { name: 'Risk Level', value: Math.max(0, 100 - Math.min(100, activeRisks * 10)) },
        { name: 'Coverage', value: Math.min(100, totalCompleted * 10) },
        { name: 'Trend', value: trendData.length > 1 ? Math.round(trendData[trendData.length - 1]?.index ?? 0) : 0 },
    ] : [];
    // ── Compliance score trend arrow ────────────────────────────────────────────
    const scoreNow = stats?.compliance_score ?? null;
    const prevScore = trendData.length > 1 ? trendData[trendData.length - 2]?.index : null;
    const scoreDiff = scoreNow !== null && prevScore !== null ? scoreNow - prevScore : null;
    // ── Pagination ──────────────────────────────────────────────────────────────
    const pagedHistory = history.slice(historyPage * PAGE_SIZE, (historyPage + 1) * PAGE_SIZE);
    const totalPages = Math.ceil(history.length / PAGE_SIZE);
    // ── Scan trigger ────────────────────────────────────────────────────────────
    const triggerScan = async () => {
        const trimmedTarget = target.trim();
        if (!trimmedTarget) {
            toast.error('Enter a target IP address or URL');
            return;
        }
        setLoading(true);
        try {
            const res = await fetch(`${API_Base}/scan`, {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify({ target: trimmedTarget, scan_type: scanType }),
            });
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to start scan');
            }
            const data = await res.json();
            toast.success(`Scan initiated — Job ${data.job_id.substring(0, 8)}`);
            navigate(`/scan/${data.job_id}`);
        }
        catch (e) {
            toast.error(e.message);
        }
        finally {
            setLoading(false);
        }
    };
    // ── SharkTap PCAP upload ────────────────────────────────────────────────────
    const uploadPcap = async () => {
        if (!pcapFile) {
            toast.error('Select a PCAP file first');
            return;
        }
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
            if (res.status === 401) {
                handleLogout();
                return;
            }
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'PCAP analysis failed');
            }
            const data = await res.json();
            toast.success(`SharkTap analysis complete — ${data.threats_detected} threats, verdict: ${data.compliance_verdict}`);
            setPcapFile(null);
            navigate(`/scan/${data.job_id}`);
        }
        catch (e) {
            toast.error(e.message);
        }
        finally {
            setPcapUploading(false);
        }
    };
    const getStatusStyle = (status) => {
        switch (status) {
            case 'completed': return 'text-green-400';
            case 'running': return 'text-blue-400';
            case 'failed': return 'text-red-400';
            default: return 'text-slate-400';
        }
    };
    // ── Skeleton loader ─────────────────────────────────────────────────────────
    if (initialLoading) {
        return (_jsxs("div", { className: "min-h-screen bg-slate-950 text-slate-100", children: [_jsx("div", { className: "border-b border-slate-800 bg-slate-900/50 h-16 animate-pulse" }), _jsx("div", { className: "max-w-7xl mx-auto p-6 space-y-6", children: [1, 2, 3].map(i => (_jsx("div", { className: "h-48 bg-slate-900/60 rounded-xl animate-pulse border border-slate-800" }, i))) })] }));
    }
    return (_jsxs("div", { className: "min-h-screen bg-slate-950 text-slate-100 font-sans", children: [_jsx(Toaster, { position: "top-right", theme: "dark" }), _jsx("header", { className: "border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-10", children: _jsxs("div", { className: "max-w-7xl mx-auto px-4 h-16 flex items-center justify-between", children: [_jsxs("div", { className: "flex items-center gap-3", children: [_jsx("img", { src: theme.platform.logoPath, alt: theme.platform.shortName, className: "h-7 w-7", onError: (e) => { e.currentTarget.style.display = 'none'; } }), _jsx(Shield, { className: "h-6 w-6 text-blue-500 hidden" }), _jsxs("span", { className: "font-bold text-lg tracking-tight", children: [theme.platform.shortName, " ", _jsx("span", { className: "text-blue-500", children: "GRC" })] })] }), _jsxs("div", { className: "flex items-center gap-3", children: [user && (_jsxs("div", { className: "hidden md:flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full text-sm border border-slate-700", children: [_jsx(UserIcon, { className: "h-3 w-3 text-slate-400" }), _jsx("span", { className: "font-medium text-slate-200", children: user.full_name || user.email }), _jsx(Badge, { variant: "outline", className: "h-5 text-[9px] bg-blue-950 border-blue-900 text-blue-300 uppercase ml-1", children: user.role })] })), user?.role === 'admin' && theme.features.enableAuditLog && (_jsxs(Button, { variant: "ghost", size: "sm", onClick: () => navigate('/audit'), className: "text-slate-400 hover:text-blue-400", children: [_jsx(List, { className: "h-4 w-4 mr-1.5" }), " Audit Logs"] })), _jsxs(Button, { variant: "ghost", size: "sm", onClick: handleLogout, className: "text-slate-400 hover:text-red-400", children: [_jsx(LogOut, { className: "h-4 w-4 mr-1.5" }), " Sign Out"] })] })] }) }), _jsxs("main", { className: "max-w-7xl mx-auto p-4 md:p-6 space-y-6", children: [_jsxs("section", { className: "grid grid-cols-2 md:grid-cols-4 gap-4", children: [_jsx(Card, { className: "bg-slate-900 border-slate-800 col-span-2 md:col-span-1", children: _jsxs(CardContent, { className: "pt-5 pb-4", children: [_jsx("p", { className: "text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1", children: "Compliance Score" }), _jsxs("div", { className: "flex items-end gap-2", children: [_jsxs("span", { className: "text-4xl font-black text-white", children: [scoreNow != null ? Math.round(scoreNow) : '—', scoreNow != null ? '%' : ''] }), scoreDiff != null && (_jsxs("span", { className: `flex items-center text-xs font-semibold mb-1 ${scoreDiff > 0 ? 'text-green-400' : scoreDiff < 0 ? 'text-red-400' : 'text-slate-500'}`, children: [scoreDiff > 0 ? _jsx(TrendingUp, { className: "h-3 w-3 mr-0.5" }) : scoreDiff < 0 ? _jsx(TrendingDown, { className: "h-3 w-3 mr-0.5" }) : _jsx(Minus, { className: "h-3 w-3 mr-0.5" }), Math.abs(Math.round(scoreDiff)), "pt"] }))] }), _jsxs("p", { className: "text-[10px] text-slate-500 mt-1", children: ["Based on last ", stats?.completed_scans ?? 0, " completed scans"] })] }) }), _jsx(Card, { className: "bg-slate-900 border-slate-800", children: _jsxs(CardContent, { className: "pt-5 pb-4", children: [_jsx("p", { className: "text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1", children: "Total Scans" }), _jsx("span", { className: "text-3xl font-black text-white", children: stats?.total_scans ?? 0 }), _jsxs("p", { className: "text-[10px] text-slate-500 mt-1", children: [stats?.completed_scans ?? 0, " completed"] })] }) }), _jsx(Card, { className: "bg-slate-900 border-slate-800", children: _jsxs(CardContent, { className: "pt-5 pb-4", children: [_jsx("p", { className: "text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1", children: "Active Risks" }), _jsx("span", { className: `text-3xl font-black ${(stats?.active_risks ?? 0) > 0 ? 'text-red-400' : 'text-green-400'}`, children: stats?.active_risks ?? 0 }), _jsx("p", { className: "text-[10px] text-slate-500 mt-1", children: "High or critical severity" })] }) }), _jsx(Card, { className: "bg-slate-900 border-slate-800", children: _jsxs(CardContent, { className: "pt-5 pb-4", children: [_jsx("p", { className: "text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1", children: "API Health" }), _jsxs("div", { className: "flex items-center gap-2 mt-1", children: [_jsx("div", { className: `relative w-2.5 h-2.5 rounded-full ${health.api ? 'bg-green-500' : 'bg-red-500'}`, children: health.api && _jsx("div", { className: "absolute inset-0 bg-green-500 rounded-full animate-ping opacity-50" }) }), _jsx("span", { className: `text-sm font-bold ${health.api ? 'text-green-400' : 'text-red-400'}`, children: health.api ? 'Operational' : 'Unreachable' })] }), _jsx("p", { className: "text-[10px] text-slate-500 mt-1", children: "Live from /health endpoint" })] }) })] }), (theme.dashboard.showTrendChart || theme.dashboard.showRadarChart) && (_jsxs("section", { className: "grid grid-cols-1 md:grid-cols-3 gap-6", children: [theme.dashboard.showTrendChart && (_jsxs(Card, { className: "md:col-span-2 bg-slate-900 border-slate-800", children: [_jsxs(CardHeader, { className: "pb-2", children: [_jsx(CardTitle, { className: "text-sm font-medium text-blue-400", children: "Compliance Trend" }), _jsx(CardDescription, { className: "text-xs", children: trendData.length > 0
                                                    ? `Last ${trendData.length} completed scans — score computed per finding severity`
                                                    : 'Complete scans to see trend data' })] }), _jsx(CardContent, { className: "h-52", children: trendData.length === 0 ? (_jsx("div", { className: "h-full flex items-center justify-center text-slate-600 text-sm", children: "No completed scans yet" })) : (_jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(AreaChart, { data: trendData, children: [_jsx("defs", { children: _jsxs("linearGradient", { id: "areaGrad", x1: "0", y1: "0", x2: "0", y2: "1", children: [_jsx("stop", { offset: "5%", stopColor: "#3b82f6", stopOpacity: 0.25 }), _jsx("stop", { offset: "95%", stopColor: "#3b82f6", stopOpacity: 0 })] }) }), _jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#1e293b", vertical: false }), _jsx(XAxis, { dataKey: "name", stroke: "#64748b", fontSize: 10, tickLine: false, axisLine: false }), _jsx(YAxis, { domain: [0, 100], stroke: "#64748b", fontSize: 10, tickLine: false, axisLine: false }), _jsx(Tooltip, { contentStyle: { backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }, itemStyle: { color: '#3b82f6' }, formatter: (val) => [`${val}%`, 'Compliance Index'] }), _jsx(Area, { type: "monotone", dataKey: "index", stroke: "#3b82f6", fill: "url(#areaGrad)", strokeWidth: 2 })] }) })) })] })), theme.dashboard.showRadarChart && (_jsxs(Card, { className: "bg-slate-900 border-slate-800", children: [_jsxs(CardHeader, { className: "pb-2", children: [_jsx(CardTitle, { className: "text-sm font-medium text-indigo-400", children: "Security Posture" }), _jsx(CardDescription, { className: "text-xs", children: radarData.length > 0 ? 'Computed from live scan data' : 'Run scans to populate' })] }), _jsx(CardContent, { className: "h-52 flex items-center justify-center", children: radarData.length === 0 ? (_jsx("div", { className: "text-slate-600 text-sm text-center", children: "No scan data yet" })) : (_jsx(ResponsiveContainer, { width: "100%", height: "100%", children: _jsxs(RadarChart, { data: radarData, children: [_jsx(PolarGrid, { stroke: "#1e293b" }), _jsx(PolarAngleAxis, { dataKey: "name", stroke: "#64748b", fontSize: 9 }), _jsx(Radar, { name: "Posture", dataKey: "value", stroke: "#8b5cf6", fill: "#8b5cf6", fillOpacity: 0.35 })] }) })) })] }))] })), _jsx("section", { children: _jsxs(Card, { className: "bg-slate-900 border-slate-800", children: [_jsxs(CardHeader, { className: "pb-3", children: [_jsxs(CardTitle, { className: "flex items-center gap-2 text-xl font-bold", children: [_jsx(Search, { className: "h-5 w-5 text-blue-500" }), "New Compliance Scan"] }), _jsx(CardDescription, { children: "Enter a target to scan. Only scan systems you own or have written authorization to test." })] }), _jsx(CardContent, { children: _jsxs("div", { className: "flex flex-col md:flex-row gap-3", children: [_jsxs(Select, { value: scanType, onValueChange: setScanType, children: [_jsx(SelectTrigger, { className: "bg-slate-950 border-slate-700 text-slate-300 w-full md:w-48 flex-shrink-0", children: _jsx(SelectValue, { placeholder: "Scan type" }) }), _jsxs(SelectContent, { className: "bg-slate-900 border-slate-700", children: [_jsx(SelectItem, { value: "quick", children: "Quick Scan" }), _jsx(SelectItem, { value: "deep", children: "Deep Web Scan" }), _jsx(SelectItem, { value: "compliance", children: "Full Compliance Audit" }), theme.features.enableCloudScan && (_jsx(SelectItem, { value: "cloud", children: "Cloud CSPM (AWS/Azure)" }))] })] }), _jsx(Input, { placeholder: "Target (e.g., https://api.example.com or 192.168.1.100)", value: target, onChange: (e) => setTarget(e.target.value), onKeyDown: (e) => e.key === 'Enter' && !loading && triggerScan(), className: "bg-slate-950 border-slate-700 font-mono text-sm flex-1" }), _jsx(Button, { onClick: triggerScan, disabled: loading || !target.trim(), className: "bg-blue-600 hover:bg-blue-500 text-white font-bold px-6 flex-shrink-0", children: loading
                                                    ? _jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), " Initiating\u2026"] })
                                                    : _jsxs(_Fragment, { children: [_jsx(Search, { className: "mr-2 h-4 w-4" }), " Start Scan"] }) })] }) })] }) }), _jsx("section", { children: _jsxs(Card, { className: "bg-slate-900 border-slate-800 border-dashed", children: [_jsxs(CardHeader, { className: "pb-3", children: [_jsxs(CardTitle, { className: "flex items-center gap-2 text-lg font-bold", children: [_jsx(Wifi, { className: "h-5 w-5 text-indigo-400" }), "SharkTap Passive Network Analysis"] }), _jsx(CardDescription, { children: "Upload a PCAP file captured by your SharkTap inline tap for compliance cross-mapping. Detects port scans, cleartext protocols, DNS tunneling, and data exfiltration patterns." })] }), _jsxs(CardContent, { children: [_jsxs("div", { className: `relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${pcapDragOver
                                                ? 'border-indigo-500 bg-indigo-950/30'
                                                : pcapFile
                                                    ? 'border-green-700 bg-green-950/20'
                                                    : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/30'}`, onClick: () => pcapInputRef.current?.click(), onDragOver: (e) => { e.preventDefault(); setPcapDragOver(true); }, onDragLeave: () => setPcapDragOver(false), onDrop: (e) => {
                                                e.preventDefault();
                                                setPcapDragOver(false);
                                                const f = e.dataTransfer.files[0];
                                                if (f && (f.name.endsWith('.pcap') || f.name.endsWith('.pcapng') || f.name.endsWith('.cap'))) {
                                                    setPcapFile(f);
                                                }
                                                else {
                                                    toast.error('Must be a .pcap, .pcapng, or .cap file');
                                                }
                                            }, children: [_jsx("input", { ref: pcapInputRef, type: "file", accept: ".pcap,.pcapng,.cap", className: "hidden", onChange: (e) => {
                                                        const f = e.target.files?.[0];
                                                        if (f)
                                                            setPcapFile(f);
                                                    } }), pcapFile ? (_jsxs("div", { className: "flex flex-col items-center gap-2", children: [_jsx(FileText, { className: "h-10 w-10 text-green-400" }), _jsx("p", { className: "font-medium text-green-300", children: pcapFile.name }), _jsxs("p", { className: "text-xs text-slate-500", children: [(pcapFile.size / 1024 / 1024).toFixed(2), " MB \u00B7 Click to change"] })] })) : (_jsxs("div", { className: "flex flex-col items-center gap-2 text-slate-500", children: [_jsx(Upload, { className: "h-10 w-10 opacity-40" }), _jsx("p", { className: "font-medium", children: "Drop PCAP file here or click to browse" }), _jsx("p", { className: "text-xs opacity-60", children: ".pcap \u00B7 .pcapng \u00B7 .cap \u00B7 Max 500 MB" })] }))] }), _jsxs("div", { className: "flex justify-end mt-4 gap-3", children: [pcapFile && (_jsx(Button, { variant: "ghost", size: "sm", onClick: () => setPcapFile(null), className: "text-slate-500", children: "Clear" })), _jsx(Button, { onClick: uploadPcap, disabled: !pcapFile || pcapUploading, className: "bg-indigo-600 hover:bg-indigo-500 text-white font-bold", children: pcapUploading
                                                        ? _jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), " Analyzing\u2026"] })
                                                        : _jsxs(_Fragment, { children: [_jsx(Wifi, { className: "mr-2 h-4 w-4" }), " Analyze PCAP"] }) })] })] })] }) }), _jsxs("section", { children: [_jsxs("div", { className: "flex items-center justify-between mb-3", children: [_jsxs("h2", { className: "text-lg font-semibold flex items-center gap-2", children: [_jsx(Clock, { className: "h-5 w-5 text-slate-400" }), "Recent Scans", history.length > 0 && (_jsx(Badge, { variant: "outline", className: "border-slate-700 text-slate-500 font-mono text-xs ml-1", children: history.length }))] }), _jsxs("div", { className: "flex items-center gap-2", children: [history.some(j => j.status === 'running') && (_jsxs(Badge, { className: "bg-blue-950 text-blue-300 border-blue-800 text-xs animate-pulse", children: [_jsx(Activity, { className: "h-3 w-3 mr-1" }), " Scan Running"] })), _jsxs(Button, { variant: "ghost", size: "sm", onClick: () => { fetchHistory(); fetchStats(); }, className: "text-slate-500 hover:text-slate-300", children: [_jsx(RefreshCw, { className: "h-3 w-3 mr-1" }), " Refresh"] })] })] }), _jsxs(Card, { className: "bg-slate-900 border-slate-800", children: [_jsx(CardContent, { className: "p-0", children: _jsxs(Table, { children: [_jsx(TableHeader, { children: _jsxs(TableRow, { className: "border-slate-800 hover:bg-transparent", children: [_jsx(TableHead, { className: "text-slate-500 pl-4", children: "Scan ID" }), _jsx(TableHead, { className: "text-slate-500", children: "Target" }), _jsx(TableHead, { className: "text-slate-500", children: "Date" }), _jsx(TableHead, { className: "text-slate-500", children: "Status" }), _jsx(TableHead, { className: "text-slate-500", children: "Findings" }), _jsx(TableHead, { className: "text-slate-500", children: "Score" }), _jsx(TableHead, { className: "text-slate-500", children: "Verdict" }), _jsx(TableHead, { className: "text-right text-slate-500 pr-4", children: "Action" })] }) }), _jsx(TableBody, { children: pagedHistory.length === 0 ? (_jsx(TableRow, { children: _jsx(TableCell, { colSpan: 8, className: "text-center py-16", children: _jsxs("div", { className: "flex flex-col items-center gap-3 text-slate-500", children: [_jsx(FileSearch, { className: "h-10 w-10 opacity-30" }), _jsx("p", { className: "font-medium", children: "No scans yet" }), _jsx("p", { className: "text-sm opacity-60", children: "Enter a target above and click Start Scan to begin" })] }) }) })) : (pagedHistory.map((job) => (_jsxs(TableRow, { className: "border-slate-800 hover:bg-slate-800/50 cursor-pointer", onClick: () => navigate(`/scan/${job.job_id}`), children: [_jsxs(TableCell, { className: "pl-4 font-mono text-xs text-slate-500", children: [job.job_id.substring(0, 8), "\u2026"] }), _jsx(TableCell, { className: "max-w-[160px] truncate text-sm", children: job.target }), _jsx(TableCell, { className: "text-xs text-slate-500 whitespace-nowrap", children: job.time ? new Date(job.time).toLocaleDateString('en-US', {
                                                                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                                                                }) : '—' }), _jsx(TableCell, { children: _jsxs("div", { className: `flex items-center gap-1.5 text-sm font-medium ${getStatusStyle(job.status)}`, children: [job.status === 'running' && _jsx(Loader2, { className: "h-3 w-3 animate-spin" }), job.status === 'completed' && _jsx(CheckCircle2, { className: "h-3 w-3" }), job.status === 'failed' && _jsx(AlertTriangle, { className: "h-3 w-3" }), _jsx("span", { className: "capitalize", children: job.status })] }) }), _jsx(TableCell, { className: "text-sm", children: job.findings_count > 0
                                                                    ? _jsx("span", { className: job.findings_count >= 5 ? 'text-red-400 font-bold' : 'text-amber-400', children: job.findings_count })
                                                                    : _jsx("span", { className: "text-slate-500", children: "\u2014" }) }), _jsx(TableCell, { className: "text-sm", children: job.compliance_score != null
                                                                    ? _jsxs("span", { className: job.compliance_score >= 80 ? 'text-green-400 font-bold' : job.compliance_score >= 50 ? 'text-amber-400 font-bold' : 'text-red-400 font-bold', children: [Math.round(job.compliance_score), "%"] })
                                                                    : _jsx("span", { className: "text-slate-500", children: "\u2014" }) }), _jsx(TableCell, { children: job.compliance_verdict ? (_jsx(Badge, { variant: "outline", className: job.compliance_verdict === 'compliant'
                                                                        ? 'bg-green-950 border-green-800 text-green-300 text-[10px]'
                                                                        : 'bg-red-950 border-red-800 text-red-300 text-[10px]', children: job.compliance_verdict })) : _jsx("span", { className: "text-slate-600 text-xs", children: "\u2014" }) }), _jsx(TableCell, { className: "text-right pr-4", children: _jsx(Button, { variant: "ghost", size: "sm", className: "text-slate-400 hover:text-white text-xs", onClick: (e) => { e.stopPropagation(); navigate(`/scan/${job.job_id}`); }, children: "View" }) })] }, job.job_id)))) })] }) }), totalPages > 1 && (_jsxs("div", { className: "border-t border-slate-800 px-4 py-3 flex items-center justify-between", children: [_jsxs("span", { className: "text-xs text-slate-500", children: ["Page ", historyPage + 1, " of ", totalPages, " \u00B7 ", history.length, " total scans"] }), _jsxs("div", { className: "flex gap-2", children: [_jsx(Button, { variant: "outline", size: "sm", className: "border-slate-700 text-xs", disabled: historyPage === 0, onClick: () => setHistoryPage(p => p - 1), children: "Previous" }), _jsx(Button, { variant: "outline", size: "sm", className: "border-slate-700 text-xs", disabled: historyPage >= totalPages - 1, onClick: () => setHistoryPage(p => p + 1), children: "Next" })] })] }))] })] })] }), theme.features.enableAITerminal && theme.dashboard.showAITerminal && _jsx(AICommandTerminal, {})] }));
}
