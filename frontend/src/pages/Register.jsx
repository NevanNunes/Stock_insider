import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Eye, EyeOff, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';

const TRADER_ARCHETYPES = [
  { value: 'Diversified', label: 'Diversified (Balanced)', desc: 'Trades broad symbols, moderate volatility' },
  { value: 'Conservative', label: 'Conservative (Low Risk)', desc: 'Lower quantities, steady blue-chip equities' },
  { value: 'Momentum Trader', label: 'Momentum Trader', desc: 'Frequent trades capitalizing on high-volume movers' },
  { value: 'Swing Trader', label: 'Swing Trader', desc: 'Multi-day holding horizons with larger positions' },
  { value: 'Sector-Focused', label: 'Sector-Focused', desc: 'Concentrated in specific industry verticals' },
  { value: 'Active', label: 'Active Day Trader', desc: 'High daily volume and intraday executions' },
];

const SECTORS = ['IT', 'Finance', 'Energy', 'Pharma', 'Automobile', 'FMCG', 'Infrastructure'];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'trader',
    trader_type: 'Diversified',
    expected_trade_size: 100000,
    preferred_sectors: ['IT', 'Finance'],
  });

  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleSector = (sec) => {
    setForm((prev) => {
      const exists = prev.preferred_sectors.includes(sec);
      const next = exists
        ? prev.preferred_sectors.filter((s) => s !== sec)
        : [...prev.preferred_sectors, sec];
      return { ...prev, preferred_sectors: next };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username.trim() || !form.email.trim() || !form.password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (form.preferred_sectors.length === 0) {
      setError('Please select at least one preferred sector.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const payload = {
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
        trader_type: form.trader_type,
        expected_trade_size: Number(form.expected_trade_size) || 100000,
        preferred_sectors: form.preferred_sectors.join(';'),
      };

      const user = await register(payload);
      navigate(user.role === 'admin' ? '/dashboard' : '/terminal', { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Registration failed. Username or email may already be in use.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-xl) var(--space-md)',
      background: 'var(--bg-deep)',
    }}>
      {/* Background ambient orbs */}
      <div style={{
        position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0,
      }}>
        <div style={{ position: 'absolute', top: '10%', right: '15%', width: 450, height: 450, borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%)', filter: 'blur(50px)' }} />
        <div style={{ position: 'absolute', bottom: '10%', left: '10%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)', filter: 'blur(50px)' }} />
      </div>

      <div style={{ width: '100%', maxWidth: 540, position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-lg)' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 56, height: 56, borderRadius: 'var(--radius-lg)',
            background: 'linear-gradient(135deg, rgba(16,185,129,0.2), rgba(59,130,246,0.2))',
            border: '1px solid var(--border-glow)',
            marginBottom: 'var(--space-sm)',
            boxShadow: '0 0 35px rgba(16,185,129,0.15)',
          }}>
            <UserPlus size={28} color="var(--accent-green)" />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 4 }}>Create Account</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Onboard as a Trader or Compliance Officer
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: 'var(--space-xl)' }}>
          {/* Onboarding Surveillance Notice */}
          <div style={{
            display: 'flex', gap: 10, alignItems: 'flex-start',
            padding: '10px 14px', borderRadius: 'var(--radius-md)',
            background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
            marginBottom: 'var(--space-md)', fontSize: '0.78rem', color: 'var(--text-secondary)',
          }}>
            <ShieldCheck size={18} color="var(--accent-blue)" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              <strong>Surveillance Baseline Setup:</strong> New accounts automatically provision a simulated trader profile with baseline metrics, allowing statistical anomaly detection (Z-Score & Isolation Forest) to work from Day 1.
            </span>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {/* Account Role Selector */}
            <div className="form-group">
              <label className="form-label">Account Role</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setForm({ ...form, role: 'trader' })}
                  className={`btn btn-sm ${form.role === 'trader' ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ justifyContent: 'center' }}
                >
                  Trader Account
                </button>
                <button
                  type="button"
                  onClick={() => setForm({ ...form, role: 'admin' })}
                  className={`btn btn-sm ${form.role === 'admin' ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ justifyContent: 'center' }}
                >
                  Compliance Admin
                </button>
              </div>
            </div>

            {/* Credentials */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label htmlFor="reg-username" className="form-label">Username *</label>
                <input
                  id="reg-username"
                  type="text"
                  className="form-input"
                  placeholder="e.g. trader_sam"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="reg-email" className="form-label">Email Address *</label>
                <input
                  id="reg-email"
                  type="email"
                  className="form-input"
                  placeholder="sam@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label htmlFor="reg-password" className="form-label">Password *</label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="reg-password"
                    type={showPw ? 'text' : 'password'}
                    className="form-input"
                    placeholder="Min 6 characters"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    style={{ paddingRight: '2.5rem' }}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    style={{
                      position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)',
                      display: 'flex', alignItems: 'center',
                    }}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="reg-confirm" className="form-label">Confirm Password *</label>
                <input
                  id="reg-confirm"
                  type={showPw ? 'text' : 'password'}
                  className="form-input"
                  placeholder="Re-enter password"
                  value={form.confirmPassword}
                  onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                  required
                />
              </div>
            </div>

            {/* Trader Profiling Section (only shown if role is trader) */}
            {form.role === 'trader' && (
              <>
                <div className="divider" style={{ margin: '4px 0' }} />

                <div className="form-group">
                  <label htmlFor="reg-archetype" className="form-label">
                    Trading Archetype (Behavioral Profile)
                  </label>
                  <select
                    id="reg-archetype"
                    className="form-select"
                    value={form.trader_type}
                    onChange={(e) => setForm({ ...form, trader_type: e.target.value })}
                  >
                    {TRADER_ARCHETYPES.map((a) => (
                      <option key={a.value} value={a.value}>
                        {a.label} — {a.desc}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="reg-tradesize" className="form-label">
                    Expected Average Trade Size (₹ Notional)
                  </label>
                  <select
                    id="reg-tradesize"
                    className="form-select"
                    value={form.expected_trade_size}
                    onChange={(e) => setForm({ ...form, expected_trade_size: Number(e.target.value) })}
                  >
                    <option value={25000}>₹25,000 (Small Retail)</option>
                    <option value={50000}>₹50,000 (Standard Retail)</option>
                    <option value={100000}>₹100,000 (Moderate Trader)</option>
                    <option value={250000}>₹250,000 (Active Swing Trader)</option>
                    <option value={500000}>₹500,000 (High Net Worth)</option>
                    <option value={1000000}>₹1,000,000+ (Institutional / Block)</option>
                  </select>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Initializes the mean & standard deviation for Z-Score statistical anomaly tracking.
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Preferred Trading Sectors</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {SECTORS.map((sec) => {
                      const selected = form.preferred_sectors.includes(sec);
                      return (
                        <button
                          key={sec}
                          type="button"
                          onClick={() => toggleSector(sec)}
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.75rem',
                            borderRadius: 'var(--radius-sm)',
                            border: `1px solid ${selected ? 'var(--accent-blue)' : 'var(--border-subtle)'}`,
                            background: selected ? 'rgba(59,130,246,0.2)' : 'var(--bg-card)',
                            color: selected ? '#93c5fd' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          {sec}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </>
            )}

            {error && <div className="error-message">{error}</div>}

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
            >
              {loading
                ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Creating Account...</>
                : <><UserPlus size={16} /> Complete Registration <ArrowRight size={16} /></>}
            </button>
          </form>

          {/* Link back to login */}
          <div style={{ textAlign: 'center', marginTop: 'var(--space-md)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--accent-blue)', fontWeight: 600, textDecoration: 'none' }}>
              Sign In
            </Link>
          </div>
        </div>

        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 'var(--space-md)' }}>
          Cloud Computing Mini-Project · Synthetic Market Surveillance
        </p>
      </div>
    </div>
  );
}
