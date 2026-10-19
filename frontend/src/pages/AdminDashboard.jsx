import { useState, useEffect, useCallback, useRef } from 'react';
import {
  AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { alertsAPI, tradesAPI, investigationsAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  LayoutDashboard, AlertTriangle, TrendingUp, FolderOpen, Activity, RefreshCw,
  Bell, ChevronRight,
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import AlertDetailModal from '../components/AlertDetailModal';

const RISK_COLORS = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

function MetricCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ background: `linear-gradient(135deg, ${color}, var(--text-primary))`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
        {value ?? <span style={{ width: 40, height: 30, borderRadius: 4, background: 'rgba(255,255,255,0.06)', display: 'inline-block' }} />}
      </div>
      {sub && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sub}</div>}
      <div className="metric-icon"><Icon size={40} color={color} /></div>
    </div>
  );
}

function formatCurrency(n) {
  return n ? '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#0f172a', border: '1px solid var(--border-glow)',
      borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: '0.8rem',
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  );
};

export default function AdminDashboard() {
  const { addToast } = useToast();

  // Metrics state
  const [metrics, setMetrics] = useState({ trades: null, alerts: null, highRisk: null, openCases: null });
  const [alerts, setAlerts] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [loadingTrades, setLoadingTrades] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [wsStatus, setWsStatus] = useState('disconnected');

  // Chart data derived from trades/alerts
  const [tradeVolumeData, setTradeVolumeData] = useState([]);
  const [riskDistData, setRiskDistData] = useState([]);

  const loadData = useCallback(async () => {
    // Load alerts
    setLoadingAlerts(true);
    try {
      const { data } = await alertsAPI.list({ page: 1, page_size: 20 });
      const list = Array.isArray(data) ? data : data.alerts || [];
      setAlerts(list);
      const total = data.total ?? list.length;
      const highCount = list.filter((a) => a.risk_level === 'HIGH').length;
      setMetrics((m) => ({ ...m, alerts: total, highRisk: highCount }));

      // Risk distribution
      const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
      list.forEach((a) => { if (counts[a.risk_level] !== undefined) counts[a.risk_level]++; });
      setRiskDistData([
        { name: 'HIGH', value: counts.HIGH },
        { name: 'MEDIUM', value: counts.MEDIUM },
        { name: 'LOW', value: counts.LOW },
      ]);
    } catch { } finally { setLoadingAlerts(false); }

    // Load trades
    setLoadingTrades(true);
    try {
      const { data } = await tradesAPI.list({ page: 1, page_size: 50 });
      const list = Array.isArray(data) ? data : data.trades || [];
      setTrades(list);
      setMetrics((m) => ({ ...m, trades: data.total ?? list.length }));

      // Group by day for area chart
      const byDay = {};
      list.forEach((t) => {
        const day = new Date(t.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        if (!byDay[day]) byDay[day] = { day, normal: 0, suspicious: 0 };
        if (t.alert?.risk_level === 'HIGH') byDay[day].suspicious++;
        else byDay[day].normal++;
      });
      setTradeVolumeData(Object.values(byDay).slice(-14));
    } catch { } finally { setLoadingTrades(false); }

    // Load investigations count
    try {
      const { data } = await investigationsAPI.list();
      const list = Array.isArray(data) ? data : data.investigations || [];
      const openCount = list.filter((i) => i.status === 'OPEN').length;
      setMetrics((m) => ({ ...m, openCases: openCount }));
    } catch { }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // WebSocket handler
  const handleWsMessage = useCallback((msg) => {
    if (msg.risk_level === 'HIGH' || msg.risk_level === 'MEDIUM') {
      addToast(msg);
    }
    // Refresh alerts panel
    setLoadingAlerts(true);
    alertsAPI.list({ page: 1, page_size: 20 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.alerts || [];
        setAlerts(list);
      })
      .finally(() => setLoadingAlerts(false));
    setMetrics((m) => ({ ...m, alerts: (m.alerts || 0) + 1, highRisk: msg.risk_level === 'HIGH' ? (m.highRisk || 0) + 1 : m.highRisk }));
  }, [addToast]);

  const { status } = useWebSocket(handleWsMessage);

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <LayoutDashboard size={22} color="var(--accent-blue)" />
            <h1 className="page-title">Surveillance Dashboard</h1>
          </div>
          <p className="page-subtitle">Real-time market monitoring & anomaly detection</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="ws-status">
            <div className={`ws-dot ${status}`} />
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
              {status === 'connected' ? 'Live' : status === 'polling' ? 'Polling' : status === 'connecting' ? 'Connecting...' : 'Offline'}
            </span>
          </div>
          {status === 'connected' && <div className="live-dot">LIVE</div>}
          <button className="btn btn-ghost btn-sm" onClick={loadData}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid-4" style={{ marginBottom: 'var(--space-xl)' }}>
        <MetricCard label="Total Trades Watched" value={metrics.trades} icon={Activity} color="var(--accent-cyan)" sub="All time" />
        <MetricCard label="Active Alerts" value={metrics.alerts} icon={Bell} color="var(--risk-medium)" sub="Detected by engine" />
        <MetricCard label="High-Risk Flags" value={metrics.highRisk} icon={AlertTriangle} color="var(--risk-high)" sub="Immediate review needed" />
        <MetricCard label="Open Investigations" value={metrics.openCases} icon={FolderOpen} color="var(--accent-purple)" sub="Compliance cases" />
      </div>

      {/* Charts Row */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-xl)' }}>
        {/* Trade Volume Over Time */}
        <div className="card">
          <div className="section-title" style={{ marginBottom: 'var(--space-md)' }}>
            <TrendingUp size={15} /> Trade Volume Over Time
          </div>
          {tradeVolumeData.length === 0 ? (
            <div className="empty-state" style={{ padding: 'var(--space-xl)' }}>Insufficient data for chart</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={tradeVolumeData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradNormal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradSuspicious" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--risk-high)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--risk-high)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: 8 }} />
                <Area type="monotone" dataKey="normal" name="Normal" stroke="var(--accent-blue)" fill="url(#gradNormal)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="suspicious" name="Suspicious" stroke="var(--risk-high)" fill="url(#gradSuspicious)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Risk Distribution Pie */}
        <div className="card">
          <div className="section-title" style={{ marginBottom: 'var(--space-md)' }}>
            <AlertTriangle size={15} /> Risk Distribution
          </div>
          {riskDistData.every((d) => d.value === 0) ? (
            <div className="empty-state" style={{ padding: 'var(--space-xl)' }}>No alerts to visualize</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={riskDistData}
                  cx="50%" cy="50%"
                  innerRadius={55} outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {riskDistData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Live Alerts Table */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: 'var(--space-md) var(--space-lg)', borderBottom: '1px solid var(--border)',
        }}>
          <div className="section-title" style={{ margin: 0 }}>
            <Bell size={15} /> Live Alerts Feed
          </div>
          {status === 'connected' && <div className="live-dot">LIVE</div>}
        </div>

        {loadingAlerts ? (
          <div className="loading-overlay"><div className="spinner" /><span>Loading alerts...</span></div>
        ) : alerts.length === 0 ? (
          <div className="empty-state"><Bell size={36} opacity={0.3} /><span>No alerts yet — submit a suspicious trade to generate one</span></div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>Risk</th>
                  <th>Symbol</th>
                  <th>Trader</th>
                  <th>Side</th>
                  <th>Notional</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Detected</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id} onClick={() => setSelectedAlert(a.id)}>
                    <td><RiskBadge level={a.risk_level} /></td>
                    <td><strong>{a.trade?.symbol || '—'}</strong></td>
                    <td className="td-mono">{a.trade?.trader_id || '—'}</td>
                    <td>
                      <span style={{ color: a.trade?.side === 'BUY' ? 'var(--risk-low)' : 'var(--risk-high)', fontWeight: 600 }}>
                        {a.trade?.side || '—'}
                      </span>
                    </td>
                    <td className="td-mono">{formatCurrency(a.trade?.notional_value)}</td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontWeight: 700,
                        color: a.combined_score >= 0.7 ? 'var(--risk-high)' : a.combined_score >= 0.4 ? 'var(--risk-medium)' : 'var(--risk-low)',
                      }}>
                        {a.combined_score?.toFixed(3)}
                      </span>
                    </td>
                    <td><span className={`badge badge-${a.status}`}>{a.status?.replace('_', ' ')}</span></td>
                    <td className="td-mono" style={{ fontSize: '0.75rem' }}>
                      {new Date(a.detected_at).toLocaleString()}
                    </td>
                    <td>
                      <ChevronRight size={14} color="var(--text-muted)" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedAlert && (
        <AlertDetailModal
          alertId={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onInvestigationOpened={() => { setSelectedAlert(null); loadData(); }}
        />
      )}
    </div>
  );
}
