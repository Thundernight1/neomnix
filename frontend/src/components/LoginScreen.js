import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Eye, EyeOff, Activity } from 'lucide-react';
import { Label } from './ui/label';
import { useTheme } from '../lib/useTheme';
import { motion } from 'framer-motion';
export default function LoginScreen() {
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const { theme } = useTheme();
    // Show a contextual message if the user was redirected here (e.g., expired session)
    const sessionExpired = new URLSearchParams(location.search).get('reason') === 'expired'
        || location.state?.sessionExpired === true;
    // Redirect away if already authenticated
    useEffect(() => {
        if (localStorage.getItem('token')) {
            navigate('/', { replace: true });
        }
    }, [navigate]);
    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const formData = new URLSearchParams();
            formData.append('username', email.trim());
            formData.append('password', password);
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({ detail: 'Login failed' }));
                throw new Error(data.detail || 'Incorrect email or password. Please try again.');
            }
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            if (data.force_password_change) {
                localStorage.setItem('force_password_change', 'true');
            }
            else {
                localStorage.removeItem('force_password_change');
            }
            navigate('/', { replace: true });
        }
        catch (err) {
            setError(err.message);
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { className: "min-h-screen bg-[#050B18] flex flex-col items-center justify-center p-4 relative overflow-hidden text-white", children: [_jsxs("div", { className: "fixed inset-0 overflow-hidden pointer-events-none", children: [_jsx("div", { className: "absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-[#00F2FF]/10 rounded-full blur-[150px] animate-pulse" }), _jsx("div", { className: "absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-[#7000FF]/10 rounded-full blur-[150px] animate-pulse", style: { animationDelay: '2s' } })] }), _jsxs(motion.div, { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5 }, className: "w-full max-w-md relative z-10", children: [_jsxs("div", { className: "text-center mb-8 space-y-2", children: [_jsxs("div", { className: "flex items-center justify-center gap-3 mb-4", children: [_jsx(Shield, { className: "w-12 h-12 text-[#00F2FF] filter drop-shadow-[0_0_10px_rgba(0,242,255,0.8)]" }), _jsxs("h1", { className: "text-4xl font-black tracking-tighter uppercase italic text-white", children: ["RALPH ", _jsx("span", { className: "text-[#00F2FF]", children: "LOOP" })] })] }), _jsxs("p", { className: "text-slate-400 text-xs font-mono tracking-[0.3em] flex items-center justify-center gap-2", children: [_jsx(Activity, { className: "w-3 h-3 text-[#10B981]" }), " SECURE ACCESS PORTAL"] })] }), _jsx("div", { className: "rounded-3xl p-8 relative overflow-hidden border border-white/10 shadow-[0_40px_100px_rgba(0,0,0,0.8)]", style: {
                            background: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))',
                            backdropFilter: 'blur(30px)',
                            transform: 'perspective(1000px) rotateX(2deg)',
                            boxShadow: '0 0 20px rgba(0,242,255,0.05)'
                        }, children: _jsxs("div", { className: "space-y-6", children: [_jsxs("div", { className: "text-center", children: [_jsx("h2", { className: "text-xl font-bold text-white tracking-[0.2em] uppercase", children: "AUTHENTICATION" }), _jsx("div", { className: "h-0.5 w-16 bg-[#00F2FF] mx-auto mt-2" })] }), _jsxs("form", { onSubmit: handleLogin, className: "space-y-5", noValidate: true, children: [_jsxs("div", { className: "space-y-2", children: [_jsx(Label, { className: "text-slate-400 text-[10px] uppercase font-bold tracking-widest ml-1", children: "Email Address" }), _jsx("input", { type: "email", placeholder: "admin@ralphloop.io", value: email, onChange: (e) => setEmail(e.target.value), className: "w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-white focus:outline-none focus:border-[#00F2FF] transition-all placeholder:text-slate-700", required: true })] }), _jsxs("div", { className: "space-y-2", children: [_jsx(Label, { className: "text-slate-400 text-[10px] uppercase font-bold tracking-widest ml-1", children: "Password" }), _jsxs("div", { className: "relative", children: [_jsx("input", { type: showPw ? 'text' : 'password', placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022", value: password, onChange: (e) => setPassword(e.target.value), className: "w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-white focus:outline-none focus:border-[#00F2FF] transition-all placeholder:text-slate-700 pr-12", required: true }), _jsx("button", { type: "button", className: "absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-[#00F2FF]", onClick: () => setShowPw(v => !v), children: showPw ? _jsx(EyeOff, { className: "h-4 w-4" }) : _jsx(Eye, { className: "h-4 w-4" }) })] })] }), _jsx("button", { type: "submit", className: "w-full py-4 bg-[#00F2FF] text-[#050B18] font-black uppercase tracking-[0.2em] rounded-xl hover:bg-[#00F2FF]/90 transition-all hover:scale-[1.02] shadow-[0_0_20px_rgba(0,242,255,0.3)] mt-4", disabled: loading, children: loading ? 'AUTHENTICATING...' : 'INITIATE LOGIN' })] })] }) }), _jsxs("div", { className: "mt-8 flex flex-col items-center gap-4", children: [_jsxs("div", { className: "flex items-center gap-6 text-[10px] text-slate-500 font-bold tracking-widest uppercase", children: [theme.platform.privacyPolicyUrl && (_jsx("a", { href: theme.platform.privacyPolicyUrl, target: "_blank", rel: "noopener noreferrer", className: "hover:text-cyber-cyan transition-colors", children: "Privacy" })), theme.platform.termsUrl && (_jsx("a", { href: theme.platform.termsUrl, target: "_blank", rel: "noopener noreferrer", className: "hover:text-cyber-cyan transition-colors", children: "Terms" })), theme.platform.supportEmail && (_jsx("a", { href: `mailto:${theme.platform.supportEmail}`, className: "hover:text-cyber-cyan transition-colors", children: "Support" }))] }), _jsxs("p", { className: "text-[10px] text-slate-700 font-mono italic", children: [theme.platform.name, " v", theme.platform.version, " // ", theme.platform.copyrightHolder] })] })] })] }));
}
