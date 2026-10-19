import { useToast } from '../context/ToastContext';
import { AlertTriangle, X } from 'lucide-react';
import RiskBadge from './RiskBadge';

function formatCurrency(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(n);
}

function Toast({ id, alert, onClose }) {
  return (
    <div className="toast" onClick={onClose} role="alert" aria-live="assertive">
      <div style={{ color: 'var(--risk-high)', flexShrink: 0, paddingTop: 2 }}>
        <AlertTriangle size={20} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <RiskBadge level={alert.risk_level || 'HIGH'} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>NEW ALERT</span>
        </div>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
          {alert.symbol} — {alert.side} {alert.quantity?.toLocaleString()} @ ${alert.price?.toFixed(2)}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: 4 }}>
          Trader: <strong>{alert.trader_id}</strong> · Notional: {formatCurrency(alert.notional_value)}
        </div>
        {alert.reason && (
          <div style={{
            fontSize: '0.74rem',
            color: 'var(--text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {alert.reason}
          </div>
        )}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', flexShrink: 0 }}
        aria-label="Dismiss alert"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-label="Live alert notifications">
      {toasts.map(({ id, alert }) => (
        <Toast key={id} id={id} alert={alert} onClose={() => removeToast(id)} />
      ))}
    </div>
  );
}
