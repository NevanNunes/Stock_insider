import { useState, useEffect, useCallback } from 'react';
import { alertsAPI } from '../api/client';
import { Bell, RefreshCw, Search } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import AlertDetailModal from '../components/AlertDetailModal';

function formatCurrency(n) {
  return n ? '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [filters, setFilters] = useState({ risk_level: '', status: '', page: 1, page_size: 25 });
  const [search, setSearch] = useState('');

  const loadAlerts = useCallback(() => {
    setLoading(true);
    const params = { ...filters };
    if (!params.risk_level) delete params.risk_level;
    if (!params.status) delete params.status;
    alertsAPI.list(params)
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.alerts || [];
        setAlerts(list);
        setTotal(data.total ?? list.length);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);

  const filtered = search
    ? alerts.filter((a) =>
        a.trade?.symbol?.toLowerCase().includes(search.toLowerCase()) ||
        a.trade?.trader_id?.toLowerCase().includes(search.toLowerCase()) ||
        String(a.id).includes(search)
      )
    : alerts;

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Bell size={22} color="var(--risk-medium)" />
            <h1 className="page-title">Surveillance Alerts</h1>
          </div>
          <p className="page-subtitle">{total} total alerts · Anomaly engine output</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadAlerts}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card card-sm" style={{ marginBottom: 'var(--space-lg)', display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search symbol, trader, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '2.25rem' }}
          />
        </div>
        <select
          className="form-select"
          style={{ flex: '0 1 160px' }}
          value={filters.risk_level}
          onChange={(e) => setFilters((f) => ({ ...f, risk_level: e.target.value, page: 1 }))}
        >
          <option value="">All Risk Levels</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
        <select
          className="form-select"
          style={{ flex: '0 1 160px' }}
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value, page: 1 }))}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">OPEN</option>
          <option value="UNDER_REVIEW">UNDER REVIEW</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div className="loading-overlay"><div className="spinner" /><span>Loading alerts...</span></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state"><Bell size={36} opacity={0.3} /><span>No alerts found</span></div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Risk</th>
                  <th>Symbol</th>
                  <th>Trader</th>
                  <th>Side</th>
                  <th>Notional</th>
                  <th>Score</th>
                  <th>Z-Score</th>
                  <th>Status</th>
                  <th>Detected</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id} onClick={() => setSelectedAlert(a.id)} title="Click to inspect">
                    <td className="td-mono">#{a.id}</td>
                    <td><RiskBadge level={a.risk_level} /></td>
                    <td><strong>{a.trade?.symbol || '—'}</strong></td>
                    <td className="td-mono">{a.trade?.trader_id || '—'}</td>
                    <td>
                      <span style={{ color: a.trade?.side === 'BUY' ? 'var(--risk-low)' : 'var(--risk-high)', fontWeight: 600, fontSize: '0.8rem' }}>
                        {a.trade?.side || '—'}
                      </span>
                    </td>
                    <td className="td-mono">{formatCurrency(a.trade?.notional_value)}</td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700,
                        color: a.combined_score >= 0.7 ? 'var(--risk-high)' : a.combined_score >= 0.4 ? 'var(--risk-medium)' : 'var(--risk-low)',
                      }}>
                        {a.combined_score?.toFixed(3)}
                      </span>
                    </td>
                    <td className="td-mono">
                      {a.notional_zscore != null ? a.notional_zscore.toFixed(1) + 'σ' : '—'}
                    </td>
                    <td>
                      <span className={`badge badge-${a.status}`}>{a.status?.replace('_', ' ')}</span>
                    </td>
                    <td className="td-mono" style={{ fontSize: '0.75rem' }}>
                      {new Date(a.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > filters.page_size && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 'var(--space-md)' }}>
          <button className="btn btn-ghost btn-sm" disabled={filters.page <= 1} onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}>← Prev</button>
          <span style={{ alignSelf: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Page {filters.page}</span>
          <button className="btn btn-ghost btn-sm" disabled={filters.page * filters.page_size >= total} onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}>Next →</button>
        </div>
      )}

      {selectedAlert && (
        <AlertDetailModal
          alertId={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onInvestigationOpened={() => setSelectedAlert(null)}
        />
      )}
    </div>
  );
}
