import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * ErrorBoundary — Global React error boundary.
 *
 * Catches unhandled JavaScript errors in the component tree and displays
 * a graceful fallback screen instead of a blank white page.
 * Required for enterprise production deployments.
 */
import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }
    static getDerivedStateFromError(error) {
        return { hasError: true, error, errorInfo: null };
    }
    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });
        // In production, send to your error monitoring service here
        console.error('[CyberSurX GRC] Unhandled error:', error, errorInfo);
    }
    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.href = '/';
    };
    render() {
        if (this.state.hasError) {
            return (_jsx("div", { className: "min-h-screen bg-slate-950 flex items-center justify-center p-6", children: _jsx(Card, { className: "bg-slate-900 border-red-900/50 max-w-md w-full text-center shadow-2xl shadow-red-900/10", children: _jsxs(CardContent, { className: "pt-12 pb-10 flex flex-col items-center gap-5", children: [_jsx("div", { className: "w-16 h-16 rounded-full bg-red-950/60 border border-red-800 flex items-center justify-center", children: _jsx(AlertTriangle, { className: "w-8 h-8 text-red-400" }) }), _jsxs("div", { className: "space-y-2", children: [_jsx("h2", { className: "text-xl font-bold text-white", children: "Something went wrong" }), _jsx("p", { className: "text-slate-400 text-sm leading-relaxed", children: "An unexpected error occurred. Your data is safe \u2014 this is a display error only. Click below to return to the dashboard." })] }), import.meta.env.DEV && this.state.error && (_jsx("pre", { className: "text-left text-[10px] text-red-400 bg-black/40 p-3 rounded w-full overflow-x-auto max-h-32", children: this.state.error.toString() })), _jsxs(Button, { onClick: this.handleReset, className: "bg-blue-600 hover:bg-blue-500 text-white font-semibold", children: [_jsx(RefreshCw, { className: "mr-2 h-4 w-4" }), " Return to Dashboard"] }), _jsx("p", { className: "text-[10px] text-slate-600", children: "If this problem persists, contact your platform administrator." })] }) }) }));
        }
        return this.props.children;
    }
}
