import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState, type ReactNode } from 'react';
import Dashboard from './components/Dashboard';
import LoginScreen from './components/LoginScreen';
import ScanDetail from './components/ScanDetail';
import AuditLog from './components/AuditLog';
import NotFound from './components/NotFound';
import ForcePasswordChangeModal from './components/ForcePasswordChangeModal';
import ErrorBoundary from './components/ErrorBoundary';
import { useTheme } from './lib/useTheme';
import { API_BASE } from './lib/api';

function Protected({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<'loading' | 'anonymous' | 'reset' | 'ready' | 'error'>('loading');
  const location = useLocation();
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/auth/me`, { credentials: 'include', signal: controller.signal })
      .then(async res => {
        if (res.status === 401) { setSession('anonymous'); return; }
        if (!res.ok) throw new Error('Session check failed');
        const user = await res.json();
        setSession(user.force_password_change ? 'reset' : 'ready');
      })
      .catch(error => { if (error.name !== 'AbortError') setSession('error'); });
    return () => controller.abort();
  }, [location.pathname]);
  if (session === 'loading') return <p role="status">Checking session…</p>;
  if (session === 'anonymous') return <Navigate to="/login?reason=expired" replace />;
  if (session === 'error') return <p role="alert">Cannot reach the server. Reload to retry.</p>;
  if (session === 'reset') return <ForcePasswordChangeModal onPasswordChanged={() => setSession('ready')} />;
  return children;
}

export default function App() {
  useTheme();
  return <ErrorBoundary><BrowserRouter><Routes>
    <Route path="/login" element={<LoginScreen />} />
    <Route path="/" element={<Protected><Dashboard /></Protected>} />
    <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
    <Route path="/scan/:id" element={<Protected><ScanDetail /></Protected>} />
    <Route path="/audit" element={<Protected><AuditLog /></Protected>} />
    <Route path="*" element={<NotFound />} />
  </Routes></BrowserRouter></ErrorBoundary>;
}
