import { useState, useEffect, useCallback } from 'react';
import { investigationsAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Folder, ChevronDown, ChevronUp, FileText, RefreshCw, ExternalLink, Loader } from 'lucide-react';
import RiskBadge from './RiskBadge';

const STATUS_OPTIONS = ['OPEN', 'UNDER_REVIEW', 'CLOSED'];

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status?.replace('_', ' ')}</span>;
}

function InvestigationRow({ inv, onRefresh }) {
  const { isAdmin } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(inv);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [newStatus, setNewStatus] = useState(inv.status);
  const [newNotes, setNewNotes] = useState(inv.notes || '');
  const [reportUrl, setReportUrl] = useState(inv.report_url || null);

  const loadDetail = async () => {
    setLoadingDetail(true);
    try {
      const { data } = await investigationsAPI.get(inv.id);
      setDetail(data);
      if (data.report_url) setReportUrl(data.report_url);
    } catch { /* ignore */ }
    finally { setLoadingDetail(false); }
  };

  const handleToggle = () => {
    const nextState = !expanded;
    setExpanded(nextState);
    if (nextState) loadDetail();
  };

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      await investigationsAPI.update(inv.id, { status: newStatus, notes: newNotes });
      onRefresh();
    } catch { /* ignore */ }
    finally { setUpdating(false); }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const { data } = await investigationsAPI.generateReport(inv.id);
      setReportUrl(data.report_url || null);
      onRefresh();
    } catch { /* ignore */ }
    finally { setGeneratingReport(false); }
  };

  const currentAlerts = detail?.alerts || inv.alerts || [];
  const alertCount = inv.alert_count ?? currentAlerts.length ?? inv.alerts_count ?? 1;
  const opener = inv.opened_by_username || (inv.opened_by === 1 ? 'Admin' : `User #${inv.opened_by}`);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 'var(--space-md)' }}>
      {/* Clickable Header Bar */}
      <button
        onClick={handleToggle}
        style={{
          width: '100%', background: 'none', border: 'none', cursor: 'pointer',
          padding: 'var(--space-md) var(--space-lg)',
          display: 'flex', alignItems: 'center', gap: 'var(--space-md)',
          color: 'var(--text-primary)', textAlign: 'left',
        }}
      >
        <Folder size={18} color="var(--text-accent)" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Top Row: Case #, Badges, Target Trader & Symbol, Notional */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>Case #{inv.id}</span>
            {inv.highest_risk_level && <RiskBadge level={inv.highest_risk_level} />}
            <StatusBadge status={inv.status} />
            {inv.primary_trader_id && (
              <span style={{
                fontWeight: 600, fontSize: '0.8rem', color: 'var(--accent-blue)',
                background: 'rgba(59, 130, 246, 0.12)', padding: '2px 8px', borderRadius: 4,
                fontFamily: 'var(--font-mono)'
              }}>
                {inv.primary_trader_id}
              </span>
            )}
            {inv.primary_symbol && (
              <span style={{
                fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-primary)',
                background: 'rgba(255, 255, 255, 0.08)', padding: '2px 8px', borderRadius: 4
              }}>
                {inv.primary_symbol}
              </span>
            )}
            {inv.total_notional && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                ${Math.round(inv.total_notional).toLocaleString()}
              </span>
            )}
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {alertCount} alert{alertCount !== 1 ? 's' : ''} · by {opener}
            </span>
          </div>

          {/* Subtitle Row: Descriptive Anomaly Reason or Notes */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem' }}>
            <div style={{
              flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              color: inv.summary_reason ? 'var(--text-secondary)' : 'var(--text-muted)'
            }}>
              {inv.summary_reason ? (
                <span>⚠️ {inv.summary_reason}</span>
              ) : inv.notes ? (
                <span style={{ fontStyle: 'italic' }}>📝 {inv.notes}</span>
              ) : (
                <span>Surveillance case open for investigation</span>
              )}
            </div>
            <span style={{ color: 'var(--text-muted)', flexShrink: 0, fontSize: '0.72rem' }}>
              Opened {new Date(inv.opened_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {/* Expanded Details Pane */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: 'var(--space-lg)' }}>
          {loadingDetail && (
            <div className="loading-overlay" style={{ padding: 'var(--space-md)' }}>
              <div className="spinner" />
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {/* Quick Context Summary Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: 10,
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 16px',
            }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Trader Account</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)', fontSize: '0.9rem', marginTop: 2 }}>
                  {inv.primary_trader_id || '—'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Instrument</div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginTop: 2 }}>
                  {inv.primary_symbol || '—'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Notional Value</div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                  {inv.total_notional ? `$${Math.round(inv.total_notional).toLocaleString()}` : '—'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Severity</div>
                <div style={{ marginTop: 2 }}>
                  <RiskBadge level={inv.highest_risk_level || 'LOW'} />
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Trade Code</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                  {inv.primary_trade_code || '—'}
                </div>
              </div>
            </div>

            {/* Attached Alerts List with full details */}
            {currentAlerts.length > 0 && (
              <div>
                <div className="section-title" style={{ marginBottom: 8 }}>Attached Alerts ({currentAlerts.length})</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {currentAlerts.map((a) => (
                    <div key={a.id} style={{
                      background: 'var(--bg-glass)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '10px 14px',
                      fontSize: '0.85rem',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: a.reason ? 6 : 0 }}>
                        <RiskBadge level={a.risk_level} />
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontWeight: 600 }}>Alert #{a.id}</span>
                        {a.trade && (
                          <>
                            <span style={{ fontWeight: 600 }}>{a.trade.symbol}</span>
                            <span style={{ color: a.trade.side === 'BUY' ? 'var(--risk-low)' : 'var(--risk-high)', fontWeight: 700 }}>
                              {a.trade.side}
                            </span>
                            <span className="td-mono">{a.trade.quantity?.toLocaleString()} shs @ ${a.trade.price?.toFixed(2)}</span>
                            <span className="td-mono">(${Math.round(a.trade.notional_value).toLocaleString()})</span>
                          </>
                        )}
                        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                          Score: {a.combined_score?.toFixed(3)}
                          {a.notional_zscore !== null && a.notional_zscore !== undefined && (
                            ` · Z: ${a.notional_zscore >= 0 ? '+' : ''}${a.notional_zscore.toFixed(1)}σ`
                          )}
                        </span>
                      </div>
                      {a.reason && (
                        <div style={{
                          fontSize: '0.78rem', color: 'var(--text-secondary)',
                          lineHeight: 1.4, paddingLeft: 8, borderLeft: '2px solid var(--border)', marginTop: 4
                        }}>
                          {a.reason.split('\n').filter(l => l.trim().startsWith('-')).map((line, idx) => (
                            <div key={idx} style={{ marginTop: 2 }}>{line.trim()}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Case Management & Update Form */}
            {isAdmin && (
              <div>
                <div className="section-title" style={{ marginBottom: 8 }}>Update Case</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <select className="form-select" value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                    {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                  </select>
                  <textarea
                    className="form-textarea"
                    rows={3}
                    placeholder="Add/update compliance notes..."
                    value={newNotes}
                    onChange={(e) => setNewNotes(e.target.value)}
                    style={{ resize: 'vertical', minHeight: 60 }}
                  />
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button className="btn btn-primary btn-sm" onClick={handleUpdate} disabled={updating}>
                      {updating ? <Loader size={13} className="spin-icon" /> : <RefreshCw size={13} />}
                      Save Changes
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={handleGenerateReport} disabled={generatingReport}>
                      {generatingReport ? <Loader size={13} /> : <FileText size={13} />}
                      Generate PDF Report
                    </button>
                    {reportUrl && (
                      <a
                        href={reportUrl.startsWith('file://') ? `http://localhost:8000/api/reports/${inv.id}/pdf` : reportUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-ghost btn-sm"
                      >
                        <ExternalLink size={13} /> View Report
                      </a>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function InvestigationTracker() {
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  const load = useCallback(() => {
    setLoading(true);
    investigationsAPI.list()
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.investigations || [];
        setInvestigations(list);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = statusFilter === 'all'
    ? investigations
    : investigations.filter((i) => i.status === statusFilter);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)', flexWrap: 'wrap', gap: 8 }}>
        <div className="filters-bar">
          {['all', 'OPEN', 'UNDER_REVIEW', 'CLOSED'].map((s) => (
            <button
              key={s}
              className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === 'all' ? 'All' : s.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading && <div className="loading-overlay"><div className="spinner" /><span>Loading cases...</span></div>}

      {!loading && filtered.length === 0 && (
        <div className="empty-state">
          <Folder size={36} opacity={0.3} />
          <span>No investigations found</span>
        </div>
      )}

      {filtered.map((inv) => (
        <InvestigationRow key={inv.id} inv={inv} onRefresh={load} />
      ))}
    </div>
  );
}
