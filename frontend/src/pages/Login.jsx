import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('farmer@kisansetu.demo');
  const [password, setPassword] = useState('Demo@1234');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const DEMO_ACCOUNTS = [
    { label: '🌾 Demo Farmer', email: 'farmer@kisansetu.demo' },
    { label: '🤝 Demo FPO',    email: 'fpo@kisansetu.demo'    },
    { label: '🏦 Demo Lender', email: 'lender@kisansetu.demo' },
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const { data } = await login(email, password);
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('role', data.role);
      if (data.role === 'fpo_manager') navigate('/fpo');
      else if (data.role === 'lender') navigate('/lender');
      else navigate('/passport');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally { setLoading(false); }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-logo">
          <h1>🌾 KisanSetu</h1>
          <p>Farmer Trust Passport — Portable Agricultural Economic Identity</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? <><span className="spinner" /> Logging in...</> : 'Login'}
          </button>
        </form>

        <div style={{ marginTop: 24 }}>
          <p className="muted" style={{ textAlign: 'center', marginBottom: 10 }}>Demo accounts (password: Demo@1234)</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {DEMO_ACCOUNTS.map(a => (
              <button key={a.email} className="btn btn-secondary btn-sm"
                onClick={() => { setEmail(a.email); setPassword('Demo@1234'); }}>
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
