import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { useWebSocket } from './hooks/useWebSocket';
import { useToast } from './context/ToastContext';
import { useState, useCallback } from 'react';

import Sidebar from './components/Sidebar';
import ToastContainer from './components/ToastAlert';

import Login from './pages/Login';
import Register from './pages/Register';
import AdminDashboard from './pages/AdminDashboard';
import TraderTerminal from './pages/TraderTerminal';
import Alerts from './pages/Alerts';
import Trades from './pages/Trades';
import Investigations from './pages/Investigations';

// Protected route wrapper
function ProtectedRoute({ children, adminOnly = false }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'admin') return <Navigate to="/terminal" replace />;
  return children;
}

// App shell (authenticated layout with sidebar + WebSocket)
function AppShell() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [wsStatus, setWsStatus] = useState('disconnected');

  const handleWsMessage = useCallback((msg) => {
    if (msg.risk_level === 'HIGH' || msg.risk_level === 'MEDIUM') {
      addToast(msg);
    }
  }, [addToast]);

  const { status } = useWebSocket(user ? handleWsMessage : () => {});

  return (
    <div className="app-layout">
      <Sidebar wsStatus={status} />
      <main className="main-content">
        <Routes>
          <Route path="/dashboard" element={
            <ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>
          } />
          <Route path="/alerts" element={
            <ProtectedRoute adminOnly><Alerts /></ProtectedRoute>
          } />
          <Route path="/investigations" element={
            <ProtectedRoute adminOnly><Investigations /></ProtectedRoute>
          } />
          <Route path="/terminal" element={
            <ProtectedRoute><TraderTerminal /></ProtectedRoute>
          } />
          <Route path="/trades" element={
            <ProtectedRoute><Trades /></ProtectedRoute>
          } />
          <Route path="/" element={
            <ProtectedRoute>
              {user?.role === 'admin' ? <Navigate to="/dashboard" replace /> : <Navigate to="/terminal" replace />}
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <ToastContainer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginGate />} />
            <Route path="/register" element={<RegisterGate />} />
            <Route path="/*" element={<AppShell />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

// Redirect to app if already logged in
function LoginGate() {
  const { user } = useAuth();
  if (user) return <Navigate to={user.role === 'admin' ? '/dashboard' : '/terminal'} replace />;
  return <Login />;
}

function RegisterGate() {
  const { user } = useAuth();
  if (user) return <Navigate to={user.role === 'admin' ? '/dashboard' : '/terminal'} replace />;
  return <Register />;
}

