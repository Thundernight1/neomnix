import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/**
 * ForcePasswordChangeModal — First-Login Security Gate
 *
 * Blocking modal enforcing a password change for any account provisioned
 * with a temporary password. Cannot be dismissed without completing the change.
 * Respects theme.json branding colors.
 */
import { useState } from 'react';
import { ShieldAlert, Lock, Eye, EyeOff, CheckCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useTheme } from '../lib/useTheme';
const API_BASE = import.meta.env.VITE_API_URL || '/api';
const REQUIREMENTS = [
    { label: 'At least 10 characters', test: (pw) => pw.length >= 10 },
    { label: 'One uppercase letter', test: (pw) => /[A-Z]/.test(pw) },
    { label: 'One number', test: (pw) => /[0-9]/.test(pw) },
    { label: 'One special character', test: (pw) => /[^A-Za-z0-9]/.test(pw) },
];
function passwordScore(pw) {
    return [pw.length >= 10, pw.length >= 14, /[A-Z]/.test(pw), /[0-9]/.test(pw), /[^A-Za-z0-9]/.test(pw)]
        .filter(Boolean).length;
}
const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Excellent'];
const STRENGTH_COLORS = ['', 'text-red-400', 'text-yellow-400', 'text-blue-400', 'text-green-400', 'text-green-300'];
const BAR_COLORS = ['', 'bg-red-500', 'bg-yellow-400', 'bg-blue-400', 'bg-green-400', 'bg-green-300'];
export default function ForcePasswordChangeModal({ onPasswordChanged }) {
    const { theme } = useTheme();
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const score = passwordScore(newPassword);
    const allRequirementsMet = REQUIREMENTS.every(r => r.test(newPassword));
    const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        if (newPassword !== confirmPassword) {
            setError('New passwords do not match.');
            return;
        }
        if (!allRequirementsMet) {
            setError('Password does not meet all requirements below.');
            return;
        }
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${API_BASE}/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({ detail: 'Password change failed' }));
                throw new Error(data.detail || 'Password change failed.');
            }
            localStorage.removeItem('force_password_change');
            setSuccess(true);
            setTimeout(() => onPasswordChanged(), 2000);
        }
        catch (err) {
            setError(err.message);
        }
        finally {
            setLoading(false);
        }
    };
    const primaryColor = theme.branding.primaryColor || '#3b82f6';
    return (_jsx("div", { className: "fixed inset-0 bg-slate-950/95 backdrop-blur-sm z-50 flex items-center justify-center p-4", children: _jsxs(Card, { className: "w-full max-w-md bg-slate-900 border-amber-800/50 text-slate-100 shadow-2xl shadow-amber-900/10", children: [_jsxs(CardHeader, { className: "text-center space-y-3 pt-7", children: [_jsx("div", { className: "mx-auto w-14 h-14 bg-amber-900/30 rounded-full flex items-center justify-center ring-2 ring-amber-700/40", children: _jsx(ShieldAlert, { className: "w-7 h-7 text-amber-400" }) }), _jsx(CardTitle, { className: "text-xl font-bold text-white", children: success ? 'Password Updated' : 'Security Action Required' }), _jsx(CardDescription, { className: "text-slate-400 text-sm leading-relaxed", children: success
                                ? `Your account is secured. Redirecting to ${theme.platform.shortName}…`
                                : `Your account on ${theme.platform.name} was provisioned with a temporary password. Set a permanent password to continue.` })] }), _jsx(CardContent, { className: "pb-6", children: success ? (_jsxs("div", { className: "flex flex-col items-center gap-4 py-6", children: [_jsx(CheckCircle, { className: "w-16 h-16 text-green-400" }), _jsx("p", { className: "text-slate-300 text-sm text-center", children: "Your credentials are secured and your session is active." })] })) : (_jsxs("form", { onSubmit: handleSubmit, className: "space-y-4", children: [_jsxs("div", { className: "space-y-1.5", children: [_jsx(Label, { htmlFor: "current-pw", className: "text-slate-300 text-xs uppercase tracking-wide", children: "Current (Temporary) Password" }), _jsxs("div", { className: "relative", children: [_jsx(Input, { id: "current-pw", type: showCurrent ? 'text' : 'password', autoComplete: "current-password", value: currentPassword, onChange: (e) => setCurrentPassword(e.target.value), className: "bg-slate-950 border-slate-700 pr-10", placeholder: "Enter your current password", required: true, autoFocus: true }), _jsx("button", { type: "button", "aria-label": showCurrent ? 'Hide' : 'Show', "aria-pressed": showCurrent, className: "absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300", onClick: () => setShowCurrent(v => !v), children: showCurrent ? _jsx(EyeOff, { className: "h-4 w-4" }) : _jsx(Eye, { className: "h-4 w-4" }) })] })] }), _jsxs("div", { className: "space-y-1.5", children: [_jsx(Label, { htmlFor: "new-pw", className: "text-slate-300 text-xs uppercase tracking-wide", children: "New Password" }), _jsxs("div", { className: "relative", children: [_jsx(Input, { id: "new-pw", type: showNew ? 'text' : 'password', autoComplete: "new-password", value: newPassword, onChange: (e) => setNewPassword(e.target.value), className: "bg-slate-950 border-slate-700 pr-10", placeholder: "Minimum 10 characters", required: true }), _jsx("button", { type: "button", "aria-label": showNew ? 'Hide' : 'Show', "aria-pressed": showNew, className: "absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300", onClick: () => setShowNew(v => !v), children: showNew ? _jsx(EyeOff, { className: "h-4 w-4" }) : _jsx(Eye, { className: "h-4 w-4" }) })] }), newPassword.length > 0 && (_jsxs("div", { className: "flex items-center gap-2 mt-1", children: [_jsx("div", { className: "flex gap-1 flex-1", children: [1, 2, 3, 4, 5].map(i => (_jsx("div", { className: `h-1 flex-1 rounded-full transition-all duration-200 ${i <= score ? BAR_COLORS[score] : 'bg-slate-700'}` }, i))) }), _jsx("span", { className: `text-xs font-medium ${STRENGTH_COLORS[score]}`, children: STRENGTH_LABELS[score] })] }))] }), _jsxs("div", { className: "space-y-1.5", children: [_jsx(Label, { htmlFor: "confirm-pw", className: "text-slate-300 text-xs uppercase tracking-wide", children: "Confirm New Password" }), _jsxs("div", { className: "relative", children: [_jsx(Input, { id: "confirm-pw", type: showConfirm ? 'text' : 'password', autoComplete: "new-password", value: confirmPassword, onChange: (e) => setConfirmPassword(e.target.value), className: `bg-slate-950 border-slate-700 pr-10 ${confirmPassword.length > 0 ? (passwordsMatch ? 'border-green-700' : 'border-red-700') : ''}`, placeholder: "Re-enter new password", required: true }), _jsx("button", { type: "button", "aria-label": showConfirm ? 'Hide' : 'Show', "aria-pressed": showConfirm, className: "absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300", onClick: () => setShowConfirm(v => !v), children: showConfirm ? _jsx(EyeOff, { className: "h-4 w-4" }) : _jsx(Eye, { className: "h-4 w-4" }) })] }), confirmPassword.length > 0 && !passwordsMatch && (_jsx("p", { className: "text-xs text-red-400", children: "Passwords do not match" }))] }), _jsxs("div", { className: "bg-slate-800/50 rounded-lg p-3 space-y-1 border border-slate-700", children: [_jsxs("p", { className: "text-xs font-medium text-slate-300 flex items-center gap-1 mb-2", children: [_jsx(Lock, { className: "h-3 w-3" }), " Requirements"] }), REQUIREMENTS.map(({ label, test }) => {
                                        const met = test(newPassword);
                                        return (_jsxs("div", { className: `flex items-center gap-2 text-xs ${met ? 'text-green-400' : 'text-slate-500'}`, children: [_jsx("span", { className: "w-3 text-center", children: met ? '✓' : '○' }), label] }, label));
                                    })] }), error && (_jsx(Alert, { className: "bg-red-900/20 border-red-800 text-red-200", children: _jsx(AlertDescription, { className: "text-sm", children: error }) })), _jsx(Button, { type: "submit", disabled: loading || !allRequirementsMet || !passwordsMatch || !currentPassword, className: "w-full font-semibold text-white", style: { backgroundColor: primaryColor }, children: loading
                                    ? _jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), " Securing Account\u2026"] })
                                    : _jsxs(_Fragment, { children: [_jsx(Lock, { className: "mr-2 h-4 w-4" }), " Set Password & Continue"] }) })] })) })] }) }));
}
