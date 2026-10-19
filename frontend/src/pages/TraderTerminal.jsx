import { useState, useEffect, useCallback } from 'react';
import { tradesAPI, symbolsAPI, tradersAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Terminal, Zap, Activity, RefreshCw, Send, AlertTriangle, CheckCircle } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';

function formatCurrency(n) {
  return n ? '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
}

export default function TraderTerminal() {
  const { user } = useAuth();

  const [symbols, setSymbols] = useState([]);
  const [traders, setTraders] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loadingTrades, setLoadingTrades] = useState(true);

  // Form state
  const [form, setForm] = useState({
    trader_id: '',
    symbol: '',
    side: 'BUY',
    quantity: '',
    price: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formMsg, setFormMsg] = useState(null); // { type: 'success'|'error', text }
  const [generatingType, setGeneratingType] = useState(null); // 'suspicious' | 'normal'

  // Load reference data
  useEffect(() => {
    symbolsAPI.list().then(({ data }) => {
      const list = Array.isArray(data) ? data : data.symbols || [];
      setSymbols(list);
    }).catch(() => {});

    tradersAPI.list().then(({ data }) => {
      const list = Array.isArray(data) ? data : data.traders || [];
      setTraders(list);
    }).catch(() => {});
  }, []);

  const loadTrades = useCallback(() => {
    setLoadingTrades(true);
    tradesAPI.list({ page: 1, page_size: 30 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.trades || [];
        setTrades(list);
      })
      .catch(() => {})
      .finally(() => setLoadingTrades(false));
  }, []);

  useEffect(() => { loadTrades(); }, [loadTrades]);

  const handleFormChange = (field, value) => {
    setForm((f) => ({ ...f, [field]: value }));
    // Auto-fill price from symbol baseline
    if (field === 'symbol') {
      const sym = symbols.find((s) => s.symbol === value);
      if (sym?.baseline_price) setForm((f) => ({ ...f, symbol: value, price: sym.baseline_price.toFixed(2) }));
    }
  };

  const handleSubmitTrade = async (e) => {
    e.preventDefault();
    setFormMsg(null);
    if (!form.trader_id || !form.symbol || !form.quantity || !form.price) {
      setFormMsg({ type: 'error', text: 'All fields are required.' }); return;
    }
    setSubmitting(true);
    try {
      await tradesAPI.submit({
        trader_id: form.trader_id,
        symbol: form.symbol,
        side: form.side,
        quantity: parseFloat(form.quantity),
        price: parseFloat(form.price),
      });
      setFormMsg({ type: 'success', text: 'Trade submitted successfully! Anomaly engine is analyzing...' });
      setForm((f) => ({ ...f, quantity: '', price: '' }));
      setTimeout(loadTrades, 1500);
    } catch (err) {
      setFormMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to submit trade.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerate = async (type) => {
    setGeneratingType(type);
    setFormMsg(null);
    try {
      if (type === 'suspicious') await tradesAPI.generateSuspicious();
      else await tradesAPI.generateNormal();
      setFormMsg({ type: 'success', text: `${type === 'suspicious' ? 'Suspicious' : 'Normal'} trade generated! Watch the alert panel for results.` });
      setTimeout(loadTrades, 1500);
    } catch (err) {
      setFormMsg({ type: 'error', text: err.response?.data?.detail || 'Generation failed.' });
    } finally {
      setGeneratingType(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Terminal size={22} color="var(--accent-cyan)" />
            <h1 className="page-title">Trader Terminal</h1>
          </div>
          <p className="page-subtitle">Submit trades and monitor execution in real-time</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Logged in as: <strong style={{ color: 'var(--text-accent)' }}>{user?.username}</strong></span>
        </div>
      </div>

      {/* 1-Click Demo Buttons */}
      <div className="card" style={{ marginBottom: 'var(--space-lg)', padding: 'var(--space-md) var(--space-lg)' }}>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
          ⚡ Demo Mode — 1-Click Trade Generators
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            id="btn-generate-suspicious"
            className="btn btn-danger"
            onClick={() => handleGenerate('suspicious')}
            disabled={!!generatingType}
          >
            {generatingType === 'suspicious'
              ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Generating...</>
              : <><AlertTriangle size={15} /> Generate Suspicious Trade</>}
          </button>
          <button
            id="btn-generate-normal"
            className="btn btn-ghost"
            onClick={() => handleGenerate('normal')}
            disabled={!!generatingType}
          >
            {generatingType === 'normal'
              ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Generating...</>
              : <><CheckCircle size={15} /> Generate Normal Trade</>}
          </button>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 8 }}>
          Suspicious trade triggers a HIGH-risk alert within seconds. Watch the toast notifications.
        </p>
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Trade Form */}
        <div className="card">
          <div className="section-title" style={{ marginBottom: 'var(--space-md)' }}>
            <Send size={15} /> Manual Trade Entry
          </div>

          <form onSubmit={handleSubmitTrade} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="trade-trader">Trader ID</label>
              <select
                id="trade-trader"
                className="form-select"
                value={form.trader_id}
                onChange={(e) => handleFormChange('trader_id', e.target.value)}
              >
                <option value="">Select trader...</option>
                {traders.slice(0, 20).map((t) => (
                  <option key={t.trader_id} value={t.trader_id}>
                    {t.trader_id} ({t.trader_type})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="trade-symbol">Symbol</label>
              <select
                id="trade-symbol"
                className="form-select"
                value={form.symbol}
                onChange={(e) => handleFormChange('symbol', e.target.value)}
              >
                <option value="">Select symbol...</option>
                {symbols.map((s) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol} — {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="trade-side">Side</label>
              <select
                id="trade-side"
                className="form-select"
                value={form.side}
                onChange={(e) => handleFormChange('side', e.target.value)}
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>

            <div className="grid-2" style={{ gap: 'var(--space-sm)' }}>
              <div className="form-group">
                <label className="form-label" htmlFor="trade-qty">Quantity</label>
                <input
                  id="trade-qty"
                  type="number"
                  className="form-input"
                  placeholder="e.g. 150"
                  value={form.quantity}
                  onChange={(e) => handleFormChange('quantity', e.target.value)}
                  min="1"
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="trade-price">Price ($)</label>
                <input
                  id="trade-price"
                  type="number"
                  className="form-input"
                  placeholder="e.g. 450.00"
                  value={form.price}
                  onChange={(e) => handleFormChange('price', e.target.value)}
                  step="0.01" min="0.01"
                />
              </div>
            </div>

            {form.quantity && form.price && (
              <div style={{
                background: 'var(--bg-glass)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)', padding: '8px 12px',
                fontSize: '0.8rem', color: 'var(--text-secondary)',
              }}>
                Notional Value: <strong style={{ color: 'var(--text-accent)' }}>
                  {formatCurrency(parseFloat(form.quantity || 0) * parseFloat(form.price || 0))}
                </strong>
              </div>
            )}

            {formMsg && (
              <div className={formMsg.type === 'error' ? 'error-message' : 'success-message'}>
                {formMsg.text}
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={submitting} style={{ justifyContent: 'center' }}>
              {submitting
                ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Submitting...</>
                : <><Send size={15} /> Submit Trade</>}
            </button>
          </form>
        </div>

        {/* Recent Trades */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
            <div className="section-title" style={{ margin: 0 }}><Activity size={15} /> Recent Trades</div>
            <button className="btn btn-ghost btn-sm" onClick={loadTrades}>
              <RefreshCw size={13} />
            </button>
          </div>

          {loadingTrades ? (
            <div className="loading-overlay" style={{ padding: 'var(--space-lg)' }}><div className="spinner" /></div>
          ) : trades.length === 0 ? (
            <div className="empty-state">No trades yet</div>
          ) : (
            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th>Notional</th>
                      <th>Alert</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id || t.trade_code}>
                        <td><strong>{t.symbol}</strong></td>
                        <td>
                          <span style={{ color: t.side === 'BUY' ? 'var(--risk-low)' : 'var(--risk-high)', fontWeight: 600 }}>
                            {t.side}
                          </span>
                        </td>
                        <td className="td-mono">{t.quantity?.toLocaleString()}</td>
                        <td className="td-mono">${t.price?.toFixed(2)}</td>
                        <td className="td-mono">{formatCurrency(t.notional_value)}</td>
                        <td>
                          {t.alert ? <RiskBadge level={t.alert.risk_level} /> : <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
