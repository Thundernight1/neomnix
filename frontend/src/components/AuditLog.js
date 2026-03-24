import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Clock, User, Activity, ArrowLeft, Search, ShieldAlert, Download, RefreshCw, Filter } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, } from './ui/table';
import { Toaster, toast } from 'sonner';
import { useTheme } from '../lib/useTheme';
const API_Base = import.meta.env.VITE_API_URL || '/api';
const ACTION_META = {
    scan_initiated: { label: 'Scan Started', className: 'bg-blue-900/50 text-blue-300 border-blue-800' },
    report_downloaded: { label: 'Report Exported', className: 'bg-purple-900/50 text-purple-300 border-purple-800' },
    login: { label: 'Auth Success', className: 'bg-green-900/50 text-green-300 border-green-800' },
    failed_login: { label: 'Auth Failure', className: 'bg-red-900/50 text-red-300 border-red-800' },
    password_changed: { label: 'Password Changed', className: 'bg-amber-900/50 text-amber-300 border-amber-800' },
    user_created: { label: 'User Created', className: 'bg-indigo-900/50 text-indigo-300 border-indigo-800' },
    ai_command: { label: 'AI Command', className: 'bg-cyan-900/50 text-cyan-300 border-cyan-800' },
};
const PAGE_SIZE = 25;
export default function AuditLog() {
    const navigate = useNavigate();
    const { theme } = useTheme();
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [page, setPage] = useState(0);
    const [actionFilter, setActionFilter] = useState('all');
    const authHeaders = () => ({
        Authorization: `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json',
    });
    const fetchLogs = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_Base}/audit/logs?limit=500`, { headers: authHeaders() });
            if (res.status === 401) {
                navigate('/login');
                return;
            }
            if (res.status === 403) {
                toast.error('Access denied — Admin role required');
                navigate('/');
                return;
            }
            if (!res.ok)
                throw new Error('Failed to load audit log');
            setLogs(await res.json());
        }
        catch (e) {
            toast.error(e.message);
        }
        finally {
            setLoading(false);
        }
    }, [navigate]);
    useEffect(() => { fetchLogs(); }, [fetchLogs]);
    // ── Filtering ────────────────────────────────────────────────────────────
    const filtered = logs.filter(log => {
        const matchSearch = !searchTerm ||
            log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
            log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (log.resource ?? '').toLowerCase().includes(searchTerm.toLowerCase());
        const matchAction = actionFilter === 'all' || log.action === actionFilter;
        return matchSearch && matchAction;
    });
    const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
    const uniqueActions = [...new Set(logs.map(l => l.action))].sort();
    // Reset page when filter changes
    useEffect(() => { setPage(0); }, [searchTerm, actionFilter]);
    // ── CSV Export ────────────────────────────────────────────────────────────
    const exportCSV = () => {
        const header = ['Timestamp', 'User', 'Action', 'Resource', 'IP Address', 'Details'];
        const rows = filtered.map(log => [
            log.time,
            log.user,
            log.action,
            log.resource ?? '',
            log.ip ?? '',
            log.details ? JSON.stringify(log.details) : '',
        ]);
        const csvContent = [header, ...rows]
            .map(r => r.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            .join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 2000);
        toast.success('Audit log exported');
    };
    // ── Action badge ──────────────────────────────────────────────────────────
    const getActionBadge = (action) => {
        const meta = ACTION_META[action];
        if (meta) {
            return (_jsx(Badge, { variant: "outline", className: `text-[10px] ${meta.className}`, children: meta.label }));
        }
        // Generic fallback — replaceAll for multi-underscore action names
        return (_jsx(Badge, { variant: "outline", className: "text-slate-400 text-[10px] capitalize border-slate-700", children: action.replaceAll('_', ' ') }));
    };
    const formatTime = (t) => new Date(t).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    return (_jsxs("div", { className: "min-h-screen bg-slate-950 text-slate-100 font-sans", children: [_jsx(Toaster, { position: "top-right", theme: "dark" }), _jsx("header", { className: "border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-10", children: _jsxs("div", { className: "max-w-7xl mx-auto px-4 h-16 flex items-center justify-between", children: [_jsxs("div", { className: "flex items-center gap-4", children: [_jsxs(Button, { variant: "ghost", size: "sm", onClick: () => navigate('/'), className: "text-slate-400 hover:text-white", children: [_jsx(ArrowLeft, { className: "h-4 w-4 mr-2" }), " Dashboard"] }), _jsx("div", { className: "h-4 w-px bg-slate-700" }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx(ShieldAlert, { className: "h-5 w-5 text-blue-500" }), _jsxs("span", { className: "font-bold", children: [theme.platform.shortName, " ", _jsx("span", { className: "text-blue-500", children: "Audit Trail" })] })] })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsxs(Button, { variant: "ghost", size: "sm", onClick: fetchLogs, className: "text-slate-500 hover:text-slate-300", children: [_jsx(RefreshCw, { className: "h-3 w-3 mr-1" }), " Refresh"] }), _jsxs(Button, { variant: "outline", size: "sm", onClick: exportCSV, className: "border-slate-700 text-slate-300 hover:text-white text-xs", children: [_jsx(Download, { className: "h-3 w-3 mr-1" }), " Export CSV"] })] })] }) }), _jsxs("main", { className: "max-w-7xl mx-auto p-4 md:p-6 space-y-5", children: [_jsxs("div", { className: "flex flex-col md:flex-row gap-4 items-start md:items-center justify-between", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-2xl font-bold tracking-tight", children: "Security & Activity Log" }), _jsx("p", { className: "text-slate-400 text-sm", children: "Tamper-evident record of all platform activity \u00B7 HIPAA / SOC 2 audit trail" })] }), _jsxs("div", { className: "flex flex-col sm:flex-row gap-2 w-full md:w-auto", children: [_jsxs("div", { className: "relative", children: [_jsx(Filter, { className: "absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" }), _jsxs("select", { value: actionFilter, onChange: (e) => setActionFilter(e.target.value), className: "pl-8 pr-3 h-9 text-xs bg-slate-900 border border-slate-700 rounded-md text-slate-300 outline-none focus:border-blue-500 appearance-none cursor-pointer", children: [_jsx("option", { value: "all", children: "All events" }), uniqueActions.map(a => (_jsx("option", { value: a, children: a.replaceAll('_', ' ') }, a)))] })] }), _jsxs("div", { className: "relative", children: [_jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" }), _jsx(Input, { placeholder: "Search user, action, resource\u2026", className: "pl-9 bg-slate-900 border-slate-700 w-full sm:w-64 text-sm h-9", value: searchTerm, onChange: (e) => setSearchTerm(e.target.value) })] })] })] }), _jsxs(Card, { className: "bg-slate-900 border-slate-800 shadow-xl", children: [_jsx(CardContent, { className: "p-0", children: _jsxs(Table, { children: [_jsx(TableHeader, { children: _jsxs(TableRow, { className: "border-slate-800 hover:bg-transparent", children: [_jsx(TableHead, { className: "text-slate-500 uppercase text-[10px] font-bold tracking-widest pl-4", children: "Timestamp" }), _jsx(TableHead, { className: "text-slate-500 uppercase text-[10px] font-bold tracking-widest", children: "User" }), _jsx(TableHead, { className: "text-slate-500 uppercase text-[10px] font-bold tracking-widest", children: "Event" }), _jsx(TableHead, { className: "text-slate-500 uppercase text-[10px] font-bold tracking-widest", children: "Resource" }), _jsx(TableHead, { className: "text-slate-500 uppercase text-[10px] font-bold tracking-widest text-right pr-4", children: "Source IP" })] }) }), _jsx(TableBody, { children: loading ? (_jsx(TableRow, { children: _jsx(TableCell, { colSpan: 5, className: "text-center py-20", children: _jsxs("div", { className: "flex flex-col items-center gap-3 text-slate-500", children: [_jsx(Activity, { className: "h-8 w-8 animate-spin text-blue-500" }), _jsx("span", { className: "text-sm", children: "Loading audit data\u2026" })] }) }) })) : paged.length === 0 ? (_jsx(TableRow, { children: _jsx(TableCell, { colSpan: 5, className: "text-center py-20 text-slate-500", children: searchTerm || actionFilter !== 'all'
                                                        ? 'No events matched your filters.'
                                                        : 'No audit events recorded yet.' }) })) : (paged.map((log, idx) => (_jsxs(TableRow, { className: "border-slate-800 hover:bg-slate-800/40 transition-colors", children: [_jsx(TableCell, { className: "pl-4 font-mono text-[11px] text-slate-500 whitespace-nowrap", children: formatTime(log.time) }), _jsx(TableCell, { children: _jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: "w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0", children: _jsx(User, { className: "h-3 w-3 text-slate-400" }) }), _jsx("span", { className: "text-sm font-medium text-slate-200 truncate max-w-[160px]", children: log.user })] }) }), _jsx(TableCell, { children: getActionBadge(log.action) }), _jsx(TableCell, { className: "max-w-[200px] truncate font-mono text-xs text-slate-400", children: log.resource ?? _jsx("span", { className: "text-slate-600", children: "\u2014" }) }), _jsx(TableCell, { className: "text-right pr-4 font-mono text-[11px] text-slate-500", children: log.ip ?? '—' })] }, `${log.time}-${log.user}-${idx}`)))) })] }) }), totalPages > 1 && (_jsxs("div", { className: "border-t border-slate-800 px-4 py-3 flex items-center justify-between", children: [_jsxs("span", { className: "text-xs text-slate-500", children: [filtered.length, " events \u00B7 Page ", page + 1, " of ", totalPages] }), _jsxs("div", { className: "flex gap-2", children: [_jsx(Button, { variant: "outline", size: "sm", className: "border-slate-700 text-xs", disabled: page === 0, onClick: () => setPage(p => p - 1), children: "Previous" }), _jsx(Button, { variant: "outline", size: "sm", className: "border-slate-700 text-xs", disabled: page >= totalPages - 1, onClick: () => setPage(p => p + 1), children: "Next" })] })] }))] }), _jsx("section", { className: "grid grid-cols-1 md:grid-cols-3 gap-4", children: [
                            { icon: Shield, color: 'green', label: 'Immutability', value: 'Append-only log' },
                            { icon: Clock, color: 'blue', label: 'Retention', value: '365-day policy' },
                            { icon: Activity, color: 'purple', label: 'Coverage', value: `${logs.length} events recorded` },
                        ].map(({ icon: Icon, color, label, value }) => (_jsxs("div", { className: `p-4 bg-slate-900 border border-slate-800 rounded-lg flex items-center gap-4`, children: [_jsx("div", { className: `h-10 w-10 rounded bg-${color}-950 border border-${color}-900 flex items-center justify-center flex-shrink-0`, children: _jsx(Icon, { className: `h-5 w-5 text-${color}-500` }) }), _jsxs("div", { children: [_jsx("div", { className: "text-[10px] text-slate-500 uppercase font-bold tracking-wider", children: label }), _jsx("div", { className: "text-sm font-medium text-slate-200", children: value })] })] }, label))) })] })] }));
}
