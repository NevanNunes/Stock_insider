import { useState, useEffect, useCallback } from 'react';
import { tradesAPI } from '../api/client';
import { Activity, RefreshCw, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';

function formatCurrency(n) {
  return n ? '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
}

export default function Trades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const PAGE_SIZE = 30;

  const loadTrades = useCallback(() => {
    setLoading(true);
    tradesAPI.list({ page, page_size: PAGE_SIZE })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.trades || [];
        setTrades(list);
        setTotal(data.total ?? list.length);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => { loadTrades(); }, [loadTrades]);

  const filtered = search
    ? trades.filter((t) =>
        t.symbol?.toLowerCase().includes(search.toLowerCase()) ||
        t.trader_id?.toLowerCase().includes(search.toLowerCase()) ||
        t.trade_code?.toLowerCase().includes(search.toLowerCase())
      )
    : trades;

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={22} color="var(--accent-cyan)" />
            <h1 className="page-title">Trade History</h1>
          </div>
          <p className="page-subtitle">{total} total trades in surveillance scope</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadTrades}><RefreshCw size={13} /> Refresh</button>
      </div>

      <div className="card card-sm" style={{ marginBottom: 'var(--space-lg)' }}>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search symbol, trader ID, trade code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '2.25rem' }}
          />
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div className="loading-overlay"><div className="spinner" /><span>Loading trades...</span></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state"><Activity size={36} opacity={0.3} /><span>No trades found</span></div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>Trade Code</th>
                  <th>Trader</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Notional</th>
                  <th>Source</th>
                  <th>Alert</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.id || t.trade_code}>
                    <td className="td-mono" style={{ fontSize: '0.75rem' }}>{t.trade_code || '—'}</td>
                    <td className="td-mono">{t.trader_id}</td>
                    <td><strong>{t.symbol}</strong></td>
                    <td>
                      <span style={{ color: t.side === 'BUY' ? 'var(--risk-low)' : 'var(--risk-high)', fontWeight: 700, fontSize: '0.82rem' }}>
                        {t.side}
                      </span>
                    </td>
                    <td className="td-mono">{t.quantity?.toLocaleString()}</td>
                    <td className="td-mono">${t.price?.toFixed(2)}</td>
                    <td className="td-mono">{formatCurrency(t.notional_value)}</td>
                    <td>
                      <span className="chip">{t.source || 'manual'}</span>
                    </td>
                    <td>
                      {t.alert ? <RiskBadge level={t.alert.risk_level} /> : <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Clean</span>}
                    </td>
                    <td className="td-mono" style={{ fontSize: '0.75rem' }}>
                      {t.timestamp ? new Date(t.timestamp).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {total > PAGE_SIZE && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 'var(--space-md)', alignItems: 'center' }}>
          <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft size={14} /> Prev
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Page {page} of {Math.ceil(total / PAGE_SIZE)}
          </span>
          <button className="btn btn-ghost btn-sm" disabled={page * PAGE_SIZE >= total} onClick={() => setPage((p) => p + 1)}>
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
