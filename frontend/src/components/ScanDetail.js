import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Shield, AlertTriangle, CheckCircle, Loader2, Search, Cpu, Zap, Download, ArrowLeft, Clock, RefreshCw, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { toast } from 'sonner';
import { Toaster } from './ui/sonner';
import { motion } from 'framer-motion';
const API_Base = import.meta.env.VITE_API_URL || '/api';
// Scan phases — honest representation of what each phase means
const SCAN_PHASES = [
    { name: 'Enumeration', icon: Search, color: 'text-blue-400', description: 'Port & service discovery' },
    { name: 'Vulnerability Scan', icon: Cpu, color: 'text-indigo-400', description: 'ZAP active scan' },
    { name: 'Compliance Mapping', icon: Zap, color: 'text-amber-400', description: 'Control framework mapping' },
    { name: 'Report Generation', icon: Shield, color: 'text-green-400', description: 'Executive report' },
];
const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'];
function getSeverityStyle(severity) {
    switch (severity.toLowerCase()) {
        case 'critical': return 'text-red-400 bg-red-950/30 border-red-800';
        case 'high': return 'text-orange-400 bg-orange-950/30 border-orange-800';
        case 'medium': return 'text-yellow-400 bg-yellow-950/30 border-yellow-800';
        default: return 'text-blue-400 bg-blue-950/30 border-blue-800';
    }
}
function getSeverityBadgeStyle(severity) {
    switch (severity.toLowerCase()) {
        case 'critical': return 'bg-red-900 text-red-300 border-red-800';
        case 'high': return 'bg-orange-900 text-orange-300 border-orange-800';
        case 'medium': return 'bg-yellow-900 text-yellow-300 border-yellow-800';
        default: return 'bg-blue-900 text-blue-300 border-blue-800';
    }
}
export default function ScanDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [scan, setScan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [downloading, setDownloading] = useState(null);
    const getToken = () => localStorage.getItem('token');
    const fetchScanDetails = useCallback(async (silent = false) => {
        if (!silent)
            setLoading(true);
        try {
            const token = getToken();
            if (!token) {
                navigate('/login');
                return;
            }
            const res = await fetch(`${API_Base}/scan/${id}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 401) {
                navigate('/login');
                return;
            }
            if (res.status === 404) {
                setError('Scan not found. It may have been deleted.');
                return;
            }
            if (!res.ok)
                throw new Error(`Server error: ${res.status}`);
            const data = await res.json();
            setScan(data);
            setLastUpdated(new Date());
            setError(null);
        }
        catch (err) {
            setError(err.message || 'Failed to load scan details.');
        }
        finally {
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
    const downloadReport = async (framework) => {
        setDownloading(framework);
        let objectUrl = null;
        try {
            const token = getToken();
            const res = await fetch(`${API_Base}/reports/pdf/${id}/${framework}`, {
                headers: { Authorization: `Bearer ${token}` },
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
            setTimeout(() => { if (objectUrl)
                window.URL.revokeObjectURL(objectUrl); }, 2000);
            toast.success(`${framework} report downloaded`);
        }
        catch (err) {
            if (objectUrl)
                window.URL.revokeObjectURL(objectUrl);
            toast.error(`Failed to download ${framework} report: ${err.message}`);
        }
        finally {
            setDownloading(null);
        }
    };
    // ── Phase inference from status ─────────────────────────────────────────────
    const getCurrentPhase = () => {
        if (!scan)
            return -1;
        if (scan.status === 'completed')
            return 3;
        if (scan.status === 'failed')
            return -1;
        if (scan.status === 'pending')
            return 0;
        // 'running' — infer phase from findings count as a rough proxy
        const f = scan.findings_count || 0;
        if (f === 0)
            return 0;
        if (f < 5)
            return 1;
        if (f < 10)
            return 2;
        return 3;
    };
    const currentPhase = getCurrentPhase();
    // ── Sorted findings by severity ─────────────────────────────────────────────
    const sortedFindings = [...(scan?.details?.findings ?? [])].sort((a, b) => {
        return SEVERITY_ORDER.indexOf(a.severity.toLowerCase()) - SEVERITY_ORDER.indexOf(b.severity.toLowerCase());
    });
    const criticalCount = sortedFindings.filter(f => f.severity.toLowerCase() === 'critical').length;
    const highCount = sortedFindings.filter(f => f.severity.toLowerCase() === 'high').length;
    const mediumCount = sortedFindings.filter(f => f.severity.toLowerCase() === 'medium').length;
    const lowCount = sortedFindings.filter(f => f.severity.toLowerCase() === 'low').length;
    // ── Loading / Error states ──────────────────────────────────────────────────
    if (loading && !scan) {
        return (_jsx("div", { className: "flex items-center justify-center h-screen bg-slate-950", children: _jsxs("div", { className: "flex flex-col items-center gap-4 text-slate-400", children: [_jsx(Loader2, { className: "w-10 h-10 animate-spin text-blue-500" }), _jsx("p", { className: "text-sm", children: "Loading scan details\u2026" })] }) }));
    }
    if (error && !scan) {
        return (_jsx("div", { className: "flex items-center justify-center h-screen bg-slate-950 p-6", children: _jsx(Card, { className: "bg-slate-900 border-red-900 max-w-md w-full text-center", children: _jsxs(CardContent, { className: "pt-10 pb-8 flex flex-col items-center gap-4", children: [_jsx(XCircle, { className: "w-12 h-12 text-red-500" }), _jsx("p", { className: "text-red-300 font-medium", children: error }), _jsxs(Button, { variant: "outline", onClick: () => navigate('/'), className: "border-slate-700 text-slate-300", children: [_jsx(ArrowLeft, { className: "h-4 w-4 mr-2" }), " Return to Dashboard"] })] }) }) }));
    }
    if (!scan)
        return null;
    return (_jsxs("div", { className: "min-h-screen bg-slate-950 text-slate-100 font-sans", children: [_jsx(Toaster, { position: "top-right", theme: "dark" }), _jsx("header", { className: "border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-10", children: _jsxs("div", { className: "max-w-7xl mx-auto px-4 h-16 flex items-center justify-between", children: [_jsxs("div", { className: "flex items-center gap-4", children: [_jsxs(Button, { variant: "ghost", size: "sm", onClick: () => navigate('/'), className: "text-slate-400 hover:text-white", children: [_jsx(ArrowLeft, { className: "h-4 w-4 mr-2" }), " Dashboard"] }), _jsx("div", { className: "h-4 w-px bg-slate-700" }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx(Shield, { className: "h-5 w-5 text-blue-500" }), _jsx("span", { className: "font-bold", children: "Scan Report" })] }), _jsxs(Badge, { variant: "outline", className: "font-mono text-[10px] text-slate-500 border-slate-700", children: [scan.job_id.substring(0, 12), "\u2026"] })] }), _jsxs("div", { className: "flex items-center gap-3", children: [lastUpdated && (_jsxs("span", { className: "text-[11px] text-slate-600 flex items-center gap-1", children: [_jsx(Clock, { className: "h-3 w-3" }), " Updated ", lastUpdated.toLocaleTimeString()] })), _jsxs(Button, { variant: "ghost", size: "sm", onClick: () => fetchScanDetails(), className: "text-slate-500 hover:text-slate-300", children: [_jsx(RefreshCw, { className: "h-3 w-3 mr-1" }), " Refresh"] })] })] }) }), _jsxs("main", { className: "max-w-7xl mx-auto p-6 space-y-6", children: [_jsx("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-4", children: SCAN_PHASES.map((phase, idx) => {
                            const isDone = idx < currentPhase || scan.status === 'completed';
                            const isActive = idx === currentPhase && scan.status === 'running';
                            const isPending = idx > currentPhase && scan.status !== 'completed';
                            const isFailed = scan.status === 'failed';
                            return (_jsxs("div", { className: `relative flex flex-col items-center p-4 rounded-xl border transition-all duration-300 ${isFailed
                                    ? 'bg-red-950/20 border-red-900/50 opacity-60'
                                    : isDone
                                        ? 'bg-slate-900 border-blue-600/40 shadow-md shadow-blue-900/10'
                                        : isActive
                                            ? 'bg-slate-900 border-blue-500/60 shadow-lg shadow-blue-900/20'
                                            : isPending
                                                ? 'bg-slate-950 border-slate-800 opacity-40'
                                                : 'bg-slate-900 border-slate-800'}`, children: [_jsx(phase.icon, { className: `h-5 w-5 mb-2 ${isDone || isActive ? phase.color : 'text-slate-600'}` }), _jsx("span", { className: "text-[10px] uppercase font-bold tracking-widest text-slate-400", children: phase.name }), _jsx("span", { className: "text-[9px] text-slate-600 mt-0.5 text-center leading-tight", children: phase.description }), isDone && _jsx(CheckCircle, { className: "absolute top-2 right-2 h-3 w-3 text-green-500" }), isActive && _jsx(Loader2, { className: "absolute top-2 right-2 h-3 w-3 text-blue-500 animate-spin" })] }, phase.name));
                        }) }), _jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-3 gap-6", children: [_jsxs(Card, { className: "lg:col-span-2 bg-slate-900 border-slate-800", children: [_jsxs(CardHeader, { className: "flex flex-row items-center justify-between pb-3", children: [_jsxs(CardTitle, { className: "text-sm text-slate-400 flex items-center gap-2", children: [_jsx(Shield, { className: "h-4 w-4" }), " Scan Details"] }), scan.status === 'completed' && (_jsx("div", { className: "flex flex-wrap gap-2", children: ['HIPAA-2026', 'SOC2', 'NIST-800-53'].map((fw) => (_jsxs(Button, { size: "sm", variant: "outline", className: "h-7 text-[10px] border-slate-700 hover:border-blue-600", onClick: () => downloadReport(fw), disabled: !!downloading, children: [downloading === fw
                                                            ? _jsx(Loader2, { className: "h-3 w-3 animate-spin mr-1" })
                                                            : _jsx(Download, { className: "h-3 w-3 mr-1" }), fw] }, fw))) }))] }), _jsxs(CardContent, { className: "grid grid-cols-2 md:grid-cols-4 gap-6", children: [_jsxs("div", { children: [_jsx("div", { className: "text-[10px] uppercase font-bold text-slate-500 mb-1", children: "Target" }), _jsx("div", { className: "font-mono text-sm text-blue-200 break-all", children: scan.target })] }), _jsxs("div", { children: [_jsx("div", { className: "text-[10px] uppercase font-bold text-slate-500 mb-1", children: "Status" }), _jsxs(Badge, { variant: "outline", className: `uppercase text-[10px] ${scan.status === 'completed' ? 'bg-green-950 border-green-800 text-green-300'
                                                            : scan.status === 'running' ? 'bg-blue-950 border-blue-800 text-blue-300 animate-pulse'
                                                                : scan.status === 'failed' ? 'bg-red-950 border-red-800 text-red-300'
                                                                    : 'bg-slate-800 border-slate-700 text-slate-400'}`, children: [scan.status === 'running' && _jsx(Loader2, { className: "h-2 w-2 animate-spin mr-1" }), scan.status] })] }), _jsxs("div", { children: [_jsx("div", { className: "text-[10px] uppercase font-bold text-slate-500 mb-1", children: "Verdict" }), _jsx("div", { className: `font-black text-sm tracking-tight ${scan.compliance_verdict === 'compliant' ? 'text-green-400' : 'text-red-400'}`, children: scan.status === 'running' || scan.status === 'pending'
                                                            ? '—'
                                                            : (scan.compliance_verdict?.replace(/_/g, ' ').toUpperCase() || 'PENDING') })] }), _jsxs("div", { children: [_jsx("div", { className: "text-[10px] uppercase font-bold text-slate-500 mb-1", children: "Findings" }), _jsxs("div", { className: "flex gap-2 flex-wrap", children: [criticalCount > 0 && _jsxs("span", { className: "text-[10px] font-bold text-red-400", children: [criticalCount, " CRIT"] }), highCount > 0 && _jsxs("span", { className: "text-[10px] font-bold text-orange-400", children: [highCount, " HIGH"] }), mediumCount > 0 && _jsxs("span", { className: "text-[10px] font-bold text-yellow-400", children: [mediumCount, " MED"] }), lowCount > 0 && _jsxs("span", { className: "text-[10px] font-bold text-blue-400", children: [lowCount, " LOW"] }), scan.findings_count === 0 && scan.status === 'completed' && (_jsx("span", { className: "text-[10px] font-bold text-green-400", children: "NONE" })), (scan.status === 'running' || scan.status === 'pending') && (_jsx("span", { className: "text-[10px] text-slate-500", children: "Scanning\u2026" }))] })] })] })] }), _jsxs(Card, { className: "bg-slate-900 border-slate-800 flex flex-col items-center justify-center p-6", children: [_jsx("div", { className: "text-[10px] uppercase font-bold text-slate-500 mb-3 tracking-widest", children: "Compliance Score" }), scan.status === 'running' || scan.status === 'pending' ? (_jsxs("div", { className: "flex flex-col items-center gap-3 py-4", children: [_jsx(Loader2, { className: "w-10 h-10 animate-spin text-blue-500" }), _jsx("p", { className: "text-xs text-slate-500", children: "Computing\u2026" })] })) : (_jsxs("div", { className: "relative w-36 h-36", children: [_jsxs("svg", { className: "w-full h-full -rotate-90", viewBox: "0 0 160 160", children: [_jsx("circle", { cx: "80", cy: "80", r: "68", fill: "transparent", stroke: "#1e293b", strokeWidth: "10" }), _jsx(motion.circle, { cx: "80", cy: "80", r: "68", fill: "transparent", stroke: (scan.compliance_score ?? 0) >= 80 ? '#22c55e'
                                                            : (scan.compliance_score ?? 0) >= 50 ? '#f59e0b'
                                                                : '#ef4444', strokeWidth: "10", strokeLinecap: "round", strokeDasharray: `${2 * Math.PI * 68}`, initial: { strokeDashoffset: 2 * Math.PI * 68 }, animate: {
                                                            strokeDashoffset: 2 * Math.PI * 68 * (1 - (scan.compliance_score ?? 0) / 100),
                                                        }, transition: { duration: 1.2, ease: 'easeOut' } })] }), _jsxs("div", { className: "absolute inset-0 flex flex-col items-center justify-center", children: [_jsxs("span", { className: "text-3xl font-black text-white", children: [scan.compliance_score != null ? Math.round(scan.compliance_score) : '—', scan.compliance_score != null ? '%' : ''] }), _jsx("span", { className: "text-[9px] text-slate-500 uppercase tracking-widest mt-1", children: scan.status === 'completed' ? 'Verified' : '—' })] })] }))] })] }), (scan.status === 'running' || scan.status === 'pending') && (_jsxs(Alert, { className: "bg-blue-950/30 border-blue-800 text-blue-200", children: [_jsx(Loader2, { className: "h-4 w-4 animate-spin" }), _jsx(AlertTitle, { className: "text-blue-300 font-semibold", children: "Scan In Progress" }), _jsxs(AlertDescription, { className: "text-blue-400/80 text-sm", children: ["The scan engine is actively analyzing ", _jsx("span", { className: "font-mono font-bold", children: scan.target }), ". This page polls automatically every 8 seconds. Results will appear when the scan completes."] })] })), scan.status === 'failed' && (_jsxs(Alert, { className: "bg-red-950/30 border-red-800 text-red-200", children: [_jsx(XCircle, { className: "h-4 w-4" }), _jsx(AlertTitle, { className: "text-red-300 font-semibold", children: "Scan Failed" }), _jsx(AlertDescription, { className: "text-red-400/80 text-sm", children: "The scan could not be completed. This may be due to an unreachable target, a network timeout, or an internal worker error. Check the system logs for details, then retry from the dashboard." })] })), scan.status === 'completed' && (_jsxs(Card, { className: "bg-slate-900 border-slate-800", children: [_jsx(CardHeader, { children: _jsxs(CardTitle, { className: "flex items-center gap-2 text-lg", children: [_jsx(AlertTriangle, { className: "h-5 w-5 text-amber-400" }), "Detailed Findings", _jsxs(Badge, { variant: "outline", className: "ml-2 border-slate-700 text-slate-400 font-mono text-xs", children: [sortedFindings.length, " total"] })] }) }), _jsx(CardContent, { children: sortedFindings.length === 0 ? (_jsxs("div", { className: "text-center py-16 space-y-3", children: [_jsx(CheckCircle, { className: "mx-auto h-14 w-14 text-green-500/30" }), _jsx("p", { className: "text-green-400 font-semibold", children: "No Findings Detected" }), _jsx("p", { className: "text-slate-500 text-sm", children: "The scan completed without identifying any compliance gaps." })] })) : (_jsx(ScrollArea, { className: "max-h-[700px] pr-2", children: _jsx("div", { className: "space-y-3", children: sortedFindings.map((f, i) => (_jsxs(Alert, { className: `border ${getSeverityStyle(f.severity)}`, children: [_jsx(AlertTriangle, { className: "h-4 w-4 flex-shrink-0" }), _jsxs(AlertTitle, { className: "flex items-center gap-2 font-semibold text-xs uppercase tracking-wide", children: [_jsx(Badge, { variant: "outline", className: `text-[9px] uppercase ${getSeverityBadgeStyle(f.severity)}`, children: f.severity }), f.control && (_jsx("span", { className: "font-mono text-[10px] text-slate-500", children: f.control })), f.framework && (_jsx(Badge, { variant: "outline", className: "text-[9px] border-slate-700 text-slate-500", children: f.framework }))] }), _jsxs(AlertDescription, { className: "mt-2 space-y-2", children: [_jsx("p", { className: "text-slate-200 text-sm font-medium", children: f.description }), f.evidence && (_jsx("pre", { className: "bg-black/40 p-2.5 rounded text-[11px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap break-words", children: f.evidence })), f.remediation && (_jsxs("div", { className: "text-sm text-blue-300 bg-blue-950/20 border border-blue-900/40 rounded p-2", children: [_jsx("span", { className: "font-semibold text-blue-400", children: "Remediation: " }), f.remediation] }))] })] }, f.id ?? i))) }) })) })] }))] })] }));
}
