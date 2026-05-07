import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/// <reference types="react" />
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
import CommandCenter from './components/CommandCenter';
import LoginScreen from './components/LoginScreen';
import ScanDetail from './components/ScanDetail';
import AuditLog from './components/AuditLog';
import NotFound from './components/NotFound';
import ForcePasswordChangeModal from './components/ForcePasswordChangeModal';
import ErrorBoundary from './components/ErrorBoundary';
import { useTheme } from './lib/useTheme';
function AppInner() {
    // Initialise and apply the white-label theme once at the app root
    useTheme();
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    useEffect(() => {
        const forceChange = localStorage.getItem('force_password_change');
        if (forceChange === 'true' && localStorage.getItem('token')) {
            setShowPasswordModal(true);
        }
    }, []);
    const isAuthenticated = () => !!localStorage.getItem('token');
    // ProtectedRoute defined outside render to avoid re-creation on every render
    return (_jsxs(_Fragment, { children: [showPasswordModal && (_jsx(ForcePasswordChangeModal, { onPasswordChanged: () => setShowPasswordModal(false) })), _jsx(Router, { children: _jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(LoginScreen, {}) }), _jsx(Route, { path: "/", element: isAuthenticated() ? _jsx(CommandCenter, {}) : _jsx(Navigate, { to: "/login", replace: true }) }), _jsx(Route, { path: "/dashboard", element: isAuthenticated() ? _jsx(Dashboard, {}) : _jsx(Navigate, { to: "/login", replace: true }) }), _jsx(Route, { path: "/scan/:id", element: isAuthenticated() ? _jsx(ScanDetail, {}) : _jsx(Navigate, { to: "/login", replace: true }) }), _jsx(Route, { path: "/audit", element: isAuthenticated() ? _jsx(AuditLog, {}) : _jsx(Navigate, { to: "/login", replace: true }) }), _jsx(Route, { path: "*", element: _jsx(NotFound, {}) })] }) })] }));
}
export default function App() {
    return (_jsx(ErrorBoundary, { children: _jsx(AppInner, {}) }));
}
