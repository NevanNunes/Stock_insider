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
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [newStatus, setNewStatus] = useState(inv.status);
  const [newNotes, setNewNotes] = useState(inv.notes || '');
  const [reportUrl, setReportUrl] = useState(inv.report_url || null);

  const loadDetail = async () => {
    if (detail) return;
    setLoadingDetail(true);
    try {
      const { data } = await investigationsAPI.get(inv.id);
      setDetail(data);
    } catch { /* ignore */ }
    finally { setLoadingDetail(false); }
  };

  const handleToggle = () => {
    setExpanded((e) => !e);
    if (!expanded) loadDetail();
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

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 'var(--space-sm)' }}>
      <button
        onClick={handleToggle}
        style={{
          width: '100%', background: 'none', border: 'none', cursor: 'pointer',
          padding: 'var(--space-md) var(--space-lg)',
          display: 'flex', alignItems: 'center', gap: 'var(--space-md)',
          color: 'var(--text-primary)', textAlign: 'left',
        }}
      >
        <Folder size={16} color="var(--text-accent)" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Case #{inv.id}</span>
            <StatusBadge status={inv.status} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {inv.alerts_count ?? '?'} alert{inv.alerts_count !== 1 ? 's' : ''} · by {inv.opened_by}
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
            Opened {new Date(inv.opened_at).toLocaleString()}
          </div>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: 'var(--space-lg)' }}>
          {loadingDetail && <div className="loading-overlay" style={{ padding: 'var(--space-lg)' }}><div className="spinner" /></div>}

          {detail && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              {/* Alerts attached */}
              {detail.alerts?.length > 0 && (
                <div>
                  <div className="section-title" style={{ marginBottom: 8 }}>Attached Alerts</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {detail.alerts.map((a) => (
                      <div key={a.id} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)',
                        padding: '8px 12px', fontSize: '0.82rem',
                      }}>
                        <RiskBadge level={a.risk_level} />
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>#{a.id}</span>
                        <span>{a.trade?.symbol} {a.trade?.side} {a.trade?.quantity?.toLocaleString()}</span>
                        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                          Score: {a.combined_score?.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Update form (admin only) */}
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
                      placeholder="Add/update notes..."
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
          )}
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
