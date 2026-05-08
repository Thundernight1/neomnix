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
  return (
    <>
      {showPasswordModal && (
        <ForcePasswordChangeModal onPasswordChanged={() => setShowPasswordModal(false)} />
      )}

      <Router>
        <Routes>
          <Route path="/login" element={<LoginScreen />} />

          <Route
            path="/"
            element={isAuthenticated() ? <CommandCenter /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/dashboard"
            element={isAuthenticated() ? <Dashboard /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/scan/:id"
            element={isAuthenticated() ? <ScanDetail /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/audit"
            element={isAuthenticated() ? <AuditLog /> : <Navigate to="/login" replace />}
          />

          {/* Catch-all 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
    </>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  );
}
