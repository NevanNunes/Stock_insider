import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ShieldAlert, LayoutDashboard, Terminal, Bell, FolderOpen, LogOut, Activity, User,
} from 'lucide-react';

export default function Sidebar({ wsStatus }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItemStyle = ({ isActive }) => ({
    ...(isActive ? {} : {}),
  });

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <ShieldAlert size={22} color="var(--accent-blue)" />
          <div>
            <div className="sidebar-logo-title">MarketSurveillance</div>
            <div className="sidebar-logo-sub">Anomaly Detection</div>
          </div>
        </div>
        {/* WS connection status */}
        <div className="ws-status" style={{ marginTop: 8 }}>
          <div className={`ws-dot ${wsStatus}`} />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            {wsStatus === 'connected' ? 'Live' : wsStatus === 'polling' ? 'Polling' : wsStatus === 'connecting' ? 'Connecting...' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1 }}>
        {isAdmin && (
          <>
            <div className="nav-section-label">Surveillance</div>
            <NavLink to="/dashboard" className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <LayoutDashboard size={16} /> Dashboard
            </NavLink>
            <NavLink to="/alerts" className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <Bell size={16} /> Alerts
            </NavLink>
            <NavLink to="/investigations" className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <FolderOpen size={16} /> Investigations
            </NavLink>
          </>
        )}

        <div className="nav-section-label" style={{ marginTop: isAdmin ? 'var(--space-lg)' : 0 }}>Trading</div>
        <NavLink to="/terminal" className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
          <Terminal size={16} /> Trader Terminal
        </NavLink>
        <NavLink to="/trades" className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
          <Activity size={16} /> Trade History
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ display: 'flex', align: 'center', gap: 8, marginBottom: 12 }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.7rem', fontWeight: 700, flexShrink: 0,
          }}>
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.username}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {user?.role}
            </div>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ width: '100%' }}>
          <LogOut size={14} /> Sign Out
        </button>
      </div>
    </aside>
  );
}
