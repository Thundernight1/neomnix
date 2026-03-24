import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useRef, useEffect } from 'react';
import { Terminal, Send, Bot, User, Loader2, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { motion, AnimatePresence } from 'framer-motion';
export default function AICommandTerminal() {
    const [isOpen, setIsOpen] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([
        { role: 'bot', content: "I am CyberSurX AI. How can I assist with your compliance today?", timestamp: new Date() }
    ]);
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);
    const handleSend = async () => {
        if (!input.trim())
            return;
        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg, timestamp: new Date() }]);
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const API_BASE = import.meta.env.VITE_API_URL || '/api';
            const response = await fetch(`${API_BASE}/command`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ command: userMsg })
            });
            if (!response.ok)
                throw new Error("AI Hub unreachable");
            const data = await response.json();
            const botResponse = data.response || "Task processed successfully.";
            setMessages(prev => [...prev, { role: 'bot', content: botResponse, timestamp: new Date() }]);
        }
        catch (error) {
            setMessages(prev => [...prev, { role: 'bot', content: `Error: ${error.message}`, timestamp: new Date() }]);
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsx("div", { className: "fixed bottom-6 right-6 z-50", children: _jsx(AnimatePresence, { children: !isOpen ? (_jsx(motion.button, { initial: { scale: 0, opacity: 0 }, animate: { scale: 1, opacity: 1 }, exit: { scale: 0, opacity: 0 }, onClick: () => setIsOpen(true), className: "w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center shadow-lg shadow-blue-900/40 text-white", children: _jsx(Bot, { className: "h-6 w-6" }) })) : (_jsxs(motion.div, { initial: { y: 20, opacity: 0 }, animate: { y: 0, opacity: 1 }, exit: { y: 20, opacity: 0 }, className: `w-96 ${isMinimized ? 'h-14' : 'h-[500px]'} bg-slate-900 border border-slate-800 rounded-xl shadow-2xl flex flex-col overflow-hidden`, children: [_jsxs("div", { className: "p-3 border-b border-slate-800 bg-slate-950 flex items-center justify-between", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx(Terminal, { className: "h-4 w-4 text-blue-500" }), _jsx("span", { className: "text-sm font-bold tracking-tight uppercase", children: "Aegis AI Terminal" }), _jsx(Badge, { variant: "outline", className: "text-[10px] h-4 bg-green-950 border-green-900 text-green-400", children: "ONLINE" })] }), _jsxs("div", { className: "flex items-center gap-1", children: [_jsx(Button, { variant: "ghost", size: "icon", className: "h-6 w-6", onClick: () => setIsMinimized(!isMinimized), children: isMinimized ? _jsx(ChevronUp, { className: "h-3 w-3" }) : _jsx(ChevronDown, { className: "h-3 w-3" }) }), _jsx(Button, { variant: "ghost", size: "icon", className: "h-6 w-6", onClick: () => setIsOpen(false), children: _jsx(X, { className: "h-3 w-3" }) })] })] }), !isMinimized && (_jsxs(_Fragment, { children: [_jsxs("div", { ref: scrollRef, className: "flex-1 overflow-y-auto p-4 space-y-4 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] bg-fixed opacity-90", children: [messages.map((m, i) => (_jsx("div", { className: `flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`, children: _jsxs("div", { className: `max-w-[80%] p-3 rounded-lg text-sm ${m.role === 'user'
                                                ? 'bg-blue-600 text-white rounded-br-none'
                                                : 'bg-slate-800 text-slate-100 border border-slate-700 rounded-bl-none'}`, children: [_jsxs("div", { className: "flex items-center gap-1 mb-1 opacity-50 text-[10px] uppercase font-bold", children: [m.role === 'user' ? _jsx(User, { className: "h-3 w-3" }) : _jsx(Bot, { className: "h-3 w-3" }), m.role] }), m.content] }) }, i))), loading && (_jsx("div", { className: "flex justify-start", children: _jsx("div", { className: "bg-slate-800 p-3 rounded-lg rounded-bl-none border border-slate-700", children: _jsx(Loader2, { className: "h-4 w-4 animate-spin text-blue-500" }) }) }))] }), _jsx("div", { className: "p-3 border-t border-slate-800 bg-slate-950", children: _jsxs("form", { onSubmit: (e) => { e.preventDefault(); handleSend(); }, className: "flex gap-2", children: [_jsx(Input, { placeholder: "Enter command or question...", value: input, onChange: (e) => setInput(e.target.value), className: "bg-slate-900 border-slate-800 text-xs h-9" }), _jsx(Button, { type: "submit", size: "icon", className: "h-9 w-9 bg-blue-600 hover:bg-blue-500", children: _jsx(Send, { className: "h-3 w-3" }) })] }) })] }))] })) }) }));
}
