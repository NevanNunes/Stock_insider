import { useState, useEffect } from 'react';
import { X, AlertTriangle, BarChart2, Brain, Clock, FileWarning, ChevronRight } from 'lucide-react';
import { alertsAPI, investigationsAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import RiskBadge from './RiskBadge';

function ScoreBar({ label, value, color }) {
  const pct = Math.min(100, Math.round((value || 0) * 100));
  return (
    <div className="score-bar-wrapper">
      <div className="score-bar-label">
        <span>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', color }}>{(value || 0).toFixed(3)}</span>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function ScoreRing({ value, label }) {
  const pct = Math.min(1, value || 0);
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;
  const color = pct >= 0.7 ? 'var(--risk-high)' : pct >= 0.4 ? 'var(--risk-medium)' : 'var(--risk-low)';

  return (
    <div className="score-ring">
      <svg viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" strokeWidth="6" stroke="rgba(255,255,255,0.06)" />
        <circle
          cx="36" cy="36" r={r} fill="none" strokeWidth="6"
          stroke={color}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
        />
      </svg>
      <div className="score-ring-value" style={{ color }}>{Math.round(pct * 100)}</div>
    </div>
  );
}

export default function AlertDetailModal({ alertId, onClose, onInvestigationOpened }) {
  const { isAdmin } = useAuth();
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [escalating, setEscalating] = useState(false);
  const [notes, setNotes] = useState('');
  const [escalated, setEscalated] = useState(false);

  useEffect(() => {
    if (!alertId) return;
    setLoading(true); setError('');
    alertsAPI.get(alertId)
      .then(({ data }) => setAlert(data))
      .catch(() => setError('Failed to load alert details.'))
      .finally(() => setLoading(false));
  }, [alertId]);

  const handleEscalate = async () => {
    setEscalating(true);
    try {
      await investigationsAPI.open([alertId], notes || 'Escalated from alert inspector.');
      setEscalated(true);
      onInvestigationOpened?.();
    } catch (e) {
      setError('Failed to open investigation: ' + (e.response?.data?.detail || e.message));
    } finally {
      setEscalating(false);
    }
  };

  const t = alert?.trade;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Alert detail">
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <FileWarning size={20} color="var(--risk-high)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>Alert Inspector</div>
              {alert && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID #{alert.id}</div>}
            </div>
          </div>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close modal"><X size={16} /></button>
        </div>

        <div className="modal-body">
          {loading && <div className="loading-overlay"><div className="spinner" /><span>Loading alert...</span></div>}
          {error && <div className="error-message">{error}</div>}

          {alert && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>

              {/* Header row */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <RiskBadge level={alert.risk_level} size="lg" />
                    <span className="badge badge-" style={{
                      background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
                      color: 'var(--text-secondary)', borderRadius: 99, padding: '0.2rem 0.65rem',
                      fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
                    }}>
                      {alert.status?.replace('_', ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <Clock size={12} style={{ display: 'inline', marginRight: 4 }} />
                    {new Date(alert.detected_at).toLocaleString()}
                  </div>
                </div>
                <div className="score-ring-container">
                  <ScoreRing value={alert.combined_score} />
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Combined Score</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: alert.combined_score >= 0.7 ? 'var(--risk-high)' : alert.combined_score >= 0.4 ? 'var(--risk-medium)' : 'var(--risk-low)' }}>
                      {(alert.combined_score || 0).toFixed(3)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Trade Details */}
              {t && (
                <div className="card card-sm">
                  <div className="section-title"><BarChart2 size={15} />Trade Details</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
                    {[
                      ['Trade Code', t.trade_code],
                      ['Trader', t.trader_id],
                      ['Symbol', t.symbol],
                      ['Side', t.side],
                      ['Quantity', t.quantity?.toLocaleString()],
                      ['Price', `$${t.price?.toFixed(2)}`],
                      ['Notional Value', `$${t.notional_value?.toLocaleString(undefined, { maximumFractionDigits: 0 })}`],
                      ['Timestamp', new Date(t.timestamp).toLocaleString()],
                    ].map(([k, v]) => (
                      <div key={k}>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>{k}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>{v || '—'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Anomaly Score Breakdown */}
              <div className="card card-sm">
                <div className="section-title"><Brain size={15} />Anomaly Score Breakdown</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <ScoreBar label="Statistical Z-Score" value={alert.statistical_score} color="var(--accent-blue)" />
                  <ScoreBar label="Isolation Forest (ML)" value={alert.ml_score} color="var(--accent-purple)" />
                  <ScoreBar label="Contextual Score" value={alert.context_score} color="var(--accent-cyan)" />
                  <div className="divider" style={{ margin: '4px 0' }} />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 2 }}>Notional Z-Score</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-accent)' }}>
                        {alert.notional_zscore != null ? alert.notional_zscore.toFixed(2) + 'σ' : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 2 }}>Quantity Z-Score</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-accent)' }}>
                        {alert.quantity_zscore != null ? alert.quantity_zscore.toFixed(2) + 'σ' : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Explanation */}
              <div className="card card-sm">
                <div className="section-title"><AlertTriangle size={15} />Detection Reason</div>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
                  {alert.reason || 'No reason provided.'}
                </p>
              </div>

              {/* Escalate */}
              {isAdmin && !escalated && (
                <div className="card card-sm" style={{ borderColor: 'var(--risk-high-border)' }}>
                  <div className="section-title"><ChevronRight size={15} />Escalate to Investigation</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <textarea
                      className="form-textarea"
                      rows={3}
                      placeholder="Add compliance notes (optional)..."
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      style={{ resize: 'vertical', minHeight: 70 }}
                    />
                    <button
                      className="btn btn-danger"
                      onClick={handleEscalate}
                      disabled={escalating}
                    >
                      {escalating ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Opening...</> : <><ChevronRight size={15} /> Open Investigation</>}
                    </button>
                  </div>
                </div>
              )}

              {escalated && (
                <div className="success-message" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  ✓ Investigation opened successfully!
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
