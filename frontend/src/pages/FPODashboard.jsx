import { useState, useEffect } from 'react';
import { listMyMembers, listFpoVerifications, updateVerification } from '../api';

export default function FPODashboard() {
  const role = localStorage.getItem('role');
  const [members, setMembers] = useState([]);
  const [verifications, setVerifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (role === 'fpo_manager') {
      Promise.all([listMyMembers(), listFpoVerifications()])
        .then(([m, v]) => { setMembers(m.data); setVerifications(v.data); })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else { setLoading(false); }
  }, [role]);

  async function verify(id, status) {
    try {
      await updateVerification(id, { status, notes: `Verified via FPO dashboard` });
      setMsg(`Verification ${status}`);
      const { data } = await listFpoVerifications();
      setVerifications(data);
    } catch (e) { setMsg(e.response?.data?.detail || 'Error'); }
  }

  if (role !== 'fpo_manager') return (
    <div><div className="page-title">FPO Dashboard</div>
      <div className="card"><p className="muted">This section is for FPO managers only.</p></div>
    </div>
  );

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>;

  const pending = verifications.filter(v => v.status === 'pending');

  return (
    <div>
      <div className="page-title">🤝 FPO Dashboard</div>
      {msg && <div className="alert alert-success mb-2">{msg}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20 }}>
        {[
          { label: 'Total Members', value: members.length },
          { label: 'Pending Verifications', value: pending.length },
          { label: 'Total Verifications', value: verifications.length },
          { label: 'Verified Records', value: verifications.filter(v => v.status === 'verified').length },
        ].map(s => (
          <div className="card" key={s.label} style={{ textAlign: 'center', padding: 18, marginBottom: 0 }}>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#1a7c3a' }}>{s.value}</div>
            <div className="muted">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-title">👥 FPO Members ({members.length})</div>
        {members.length === 0 ? <p className="muted">No members yet.</p> : (
          <table>
            <thead><tr><th>Farmer ID</th><th>Membership #</th><th>Status</th><th>Joined</th><th>FPO Verified</th></tr></thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id}>
                  <td>#{m.farmer_id}</td>
                  <td>{m.membership_number || '—'}</td>
                  <td><span className={`badge ${m.status === 'active' ? 'badge-green' : 'badge-amber'}`}>{m.status}</span></td>
                  <td>{m.membership_date ? new Date(m.membership_date).toLocaleDateString('en-IN') : '—'}</td>
                  <td><span className={`badge ${m.verified ? 'badge-green' : 'badge-amber'}`}>{m.verified ? '✓' : 'No'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <div className="card-title">✅ Verification Queue ({pending.length} pending)</div>
        {verifications.length === 0 ? <p className="muted">No verifications yet.</p> : (
          <table>
            <thead><tr><th>ID</th><th>Farmer</th><th>Type</th><th>Record</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {verifications.map(v => (
                <tr key={v.id}>
                  <td>#{v.id}</td>
                  <td>#{v.farmer_id}</td>
                  <td>{v.verification_type}</td>
                  <td>{v.record_type} #{v.record_id}</td>
                  <td><span className={`badge ${v.status === 'verified' ? 'badge-green' : v.status === 'rejected' ? 'badge-red' : 'badge-amber'}`}>{v.status}</span></td>
                  <td>
                    {v.status === 'pending' && (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-primary btn-sm" onClick={() => verify(v.id, 'verified')}>✓</button>
                        <button className="btn btn-danger btn-sm"  onClick={() => verify(v.id, 'rejected')}>✗</button>
                      </div>
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
