import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';
export default function NotFound() {
    const navigate = useNavigate();
    return (_jsxs("div", { className: "min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 p-6", children: [_jsx(Shield, { className: "h-12 w-12 text-slate-700 mb-6" }), _jsx("p", { className: "text-7xl font-black text-slate-800 mb-2", children: "404" }), _jsx("h1", { className: "text-xl font-bold text-slate-300 mb-2", children: "Page Not Found" }), _jsx("p", { className: "text-slate-500 text-sm mb-8 text-center max-w-sm", children: "The page you're looking for doesn't exist or you may not have permission to access it." }), _jsxs(Button, { onClick: () => navigate('/'), className: "bg-blue-600 hover:bg-blue-500 text-white", children: [_jsx(ArrowLeft, { className: "mr-2 h-4 w-4" }), " Return to Dashboard"] })] }));
}
