import { useState, useEffect } from 'react';
import { getDataAccessHistory } from '../api';

export default function DataAccessHistory() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDataAccessHistory().then(r => setLogs(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>;

  return (
    <div>
      <div className="page-title">📜 Data Access History</div>
      <div className="alert alert-info mb-2">
        Every time someone accesses your data, it is recorded here with a tamper-evident log.
      </div>
      <div className="card">
        {logs.length === 0 ? <p className="muted">No access history yet.</p> : (
          <table>
            <thead>
              <tr>
                <th>Who</th><th>Role</th><th>Fields Accessed</th>
                <th>Purpose</th><th>When</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.id}>
                  <td>{l.accessor_name || `User #${l.accessor_user_id || '?'}`}</td>
                  <td><span className={`badge ${l.accessor_role === 'lender' ? 'badge-blue' : 'badge-green'}`}>{l.accessor_role}</span></td>
                  <td style={{ fontSize: '0.8rem' }}>{(l.fields_accessed || []).join(', ') || '—'}</td>
                  <td>{l.purpose || '—'}</td>
                  <td>{new Date(l.accessed_at).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
