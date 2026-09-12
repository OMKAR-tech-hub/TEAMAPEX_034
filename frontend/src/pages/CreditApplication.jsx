import { useState, useEffect } from 'react';
import { createCreditApplication, listCreditApplications } from '../api';

function fmt(n) { return n ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'; }

const STATUS_COLORS = { pending: 'badge-amber', under_review: 'badge-blue', approved: 'badge-green', rejected: 'badge-red' };

export default function CreditApplication() {
  const [applications, setApplications] = useState([]);
  const [form, setForm] = useState({ amount_requested: '', purpose: '', lender_type: 'regional_rural_bank' });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => { listCreditApplications().then(r => setApplications(r.data)).catch(() => {}); }, []);

  async function submit(e) {
    e.preventDefault(); setLoading(true); setMsg('');
    try {
      await createCreditApplication({ ...form, amount_requested: parseFloat(form.amount_requested) });
      setMsg('Application submitted successfully');
      const { data } = await listCreditApplications();
      setApplications(data);
      setForm({ amount_requested: '', purpose: '', lender_type: 'regional_rural_bank' });
    } catch (e) { setMsg(e.response?.data?.detail || 'Error'); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <div className="page-title">💰 Credit Application</div>
      {msg && <div className={`alert ${msg.includes('Error') || msg.includes('failed') ? 'alert-error' : 'alert-success'} mb-2`}>{msg}</div>}

      <div className="card">
        <div className="card-title">📝 New Application</div>
        <form onSubmit={submit}>
          <div className="form-row">
            <div className="form-group">
              <label>Amount Requested (₹)</label>
              <input type="number" value={form.amount_requested} min={1000} required
                onChange={e => setForm(f => ({ ...f, amount_requested: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Lender Type</label>
              <select value={form.lender_type} onChange={e => setForm(f => ({ ...f, lender_type: e.target.value }))}>
                <option value="regional_rural_bank">Regional Rural Bank</option>
                <option value="cooperative">Cooperative Bank</option>
                <option value="nbfc">NBFC</option>
                <option value="mfi">MFI</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Purpose</label>
            <textarea rows={3} value={form.purpose} required
              placeholder="e.g. Rabi wheat seed, fertilizer and irrigation expenses"
              onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} />
          </div>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? <><span className="spinner" /> Submitting...</> : 'Submit Application'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-title">📋 My Applications ({applications.length})</div>
        {applications.length === 0 ? <p className="muted">No applications yet.</p> : (
          <table>
            <thead><tr><th>ID</th><th>Amount</th><th>Purpose</th><th>Type</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              {applications.map(a => (
                <tr key={a.id}>
                  <td>#{a.id}</td>
                  <td>{fmt(a.amount_requested)}</td>
                  <td style={{ maxWidth: 200 }}>{a.purpose}</td>
                  <td>{a.lender_type || '—'}</td>
                  <td><span className={`badge ${STATUS_COLORS[a.status] || 'badge-amber'}`}>{a.status}</span></td>
                  <td>{new Date(a.application_date).toLocaleDateString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
