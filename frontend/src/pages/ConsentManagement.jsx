import { useState, useEffect } from 'react';
import { listConsents, getPendingConsents, grantConsent, revokeConsent } from '../api';

export default function ConsentManagement() {
  const [consents, setConsents] = useState([]);
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [c, p] = await Promise.all([listConsents(), getPendingConsents()]);
      setConsents(c.data);
      setPending(p.data);
    } finally { setLoading(false); }
  }

  async function handleGrant(id, fields) {
    try {
      await grantConsent(id, { consent_id: id, data_fields_granted: fields, expires_days: 90 });
      setMsg('Consent granted for 90 days');
      load();
    } catch (e) { setMsg(e.response?.data?.detail || 'Error'); }
  }

  async function handleRevoke(id) {
    try {
      await revokeConsent(id);
      setMsg('Consent revoked');
      load();
    } catch (e) { setMsg(e.response?.data?.detail || 'Error'); }
  }

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>;

  return (
    <div>
      <div className="page-title">🔐 Consent & Data Ownership</div>
      <div className="alert alert-info mb-2">
        You control who can see your data, what they can see, and for how long. You can revoke access at any time.
      </div>
      {msg && <div className="alert alert-success mb-2">{msg}</div>}

      {/* Pending requests */}
      {pending.length > 0 && (
        <div className="card">
          <div className="card-title">⏳ Pending Consent Requests ({pending.length})</div>
          {pending.map(c => (
            <div key={c.id} style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 14, marginBottom: 12 }}>
              <div className="flex-between">
                <div>
                  <strong>Lender #{c.lender_id}</strong>
                  <div className="muted" style={{ marginTop: 4 }}>{c.request_message || 'No message'}</div>
                  <div className="muted">Purpose: {c.purpose || '—'}</div>
                  <div className="muted">Requested fields: {(c.data_fields_granted || []).join(', ')}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary btn-sm"
                    onClick={() => handleGrant(c.id, c.data_fields_granted)}>
                    ✓ Grant
                  </button>
                  <button className="btn btn-danger btn-sm"
                    onClick={() => handleRevoke(c.id)}>
                    ✗ Deny
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Active/all consents */}
      <div className="card">
        <div className="card-title">📋 All Consents ({consents.length})</div>
        {consents.length === 0 ? <p className="muted">No consent records yet.</p> : (
          <table>
            <thead>
              <tr>
                <th>Lender</th><th>Fields Granted</th><th>Purpose</th>
                <th>Status</th><th>Expires</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {consents.map(c => (
                <tr key={c.id}>
                  <td>#{c.lender_id}</td>
                  <td style={{ fontSize: '0.8rem' }}>{(c.data_fields_granted || []).join(', ')}</td>
                  <td>{c.purpose || '—'}</td>
                  <td>
                    <span className={`badge ${c.is_active ? 'badge-green' : c.revoked_at ? 'badge-red' : 'badge-amber'}`}>
                      {c.is_active ? 'Active' : c.revoked_at ? 'Revoked' : 'Pending'}
                    </span>
                  </td>
                  <td>{c.expires_at ? new Date(c.expires_at).toLocaleDateString('en-IN') : '—'}</td>
                  <td>
                    {c.is_active && (
                      <button className="btn btn-danger btn-sm" onClick={() => handleRevoke(c.id)}>
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
