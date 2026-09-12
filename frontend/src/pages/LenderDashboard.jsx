import { useState, useEffect } from 'react';
import { getConsentedFarmers, getFarmerPassportForLender, getLenderApplications, makeDecision } from '../api';
import ScoreBar from '../components/ScoreBar';

function fmt(n) { return n ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'; }

export default function LenderDashboard() {
  const role = localStorage.getItem('role');
  const [farmers, setFarmers] = useState([]);
  const [applications, setApplications] = useState([]);
  const [selectedPassport, setSelectedPassport] = useState(null);
  const [selectedFarmer, setSelectedFarmer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [passportLoading, setPassportLoading] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (role === 'lender') {
      Promise.all([getConsentedFarmers(), getLenderApplications()])
        .then(([f, a]) => { setFarmers(f.data); setApplications(a.data); })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else { setLoading(false); }
  }, [role]);

  async function viewPassport(farmerId) {
    setPassportLoading(true); setSelectedFarmer(farmerId); setSelectedPassport(null);
    try {
      const { data } = await getFarmerPassportForLender(farmerId);
      setSelectedPassport(data);
    } catch (e) { setMsg(e.response?.data?.detail || 'Error loading passport'); }
    finally { setPassportLoading(false); }
  }

  async function decide(appId, status, notes) {
    try {
      await makeDecision(appId, { status, lender_notes: notes });
      setMsg(`Decision recorded: ${status}`);
      const { data } = await getLenderApplications();
      setApplications(data);
    } catch (e) { setMsg(e.response?.data?.detail || 'Error'); }
  }

  if (role !== 'lender') return (
    <div><div className="page-title">Lender Dashboard</div>
      <div className="card"><p className="muted">This section is for lenders only.</p></div>
    </div>
  );

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>;

  return (
    <div>
      <div className="page-title">🏦 Lender Dashboard</div>
      <div className="alert alert-amber mb-2">
        ⚖️ KisanSetu provides an explainable agricultural credit profile. <strong>You make the final underwriting and approval decision.</strong>
      </div>
      {msg && <div className="alert alert-success mb-2">{msg}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Consented Farmers */}
        <div>
          <div className="card">
            <div className="card-title">🌾 Farmers with Active Consent ({farmers.length})</div>
            {farmers.length === 0 ? (
              <p className="muted">No farmers have granted consent yet.</p>
            ) : (
              farmers.map(f => (
                <div key={f.farmer_id} style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 12, marginBottom: 10 }}>
                  <div className="flex-between">
                    <div>
                      <strong>{f.farmer_name}</strong>
                      <div className="muted">{f.village}, {f.district}, {f.state}</div>
                      <div className="muted" style={{ fontSize: '0.78rem' }}>
                        Fields: {(f.data_fields_granted || []).join(', ')}
                      </div>
                      <div className="muted" style={{ fontSize: '0.78rem' }}>
                        Expires: {f.expires_at ? new Date(f.expires_at).toLocaleDateString('en-IN') : '—'}
                      </div>
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={() => viewPassport(f.farmer_id)}>
                      View Passport
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Applications */}
          <div className="card">
            <div className="card-title">📋 Applications ({applications.length})</div>
            {applications.length === 0 ? <p className="muted">No applications assigned yet.</p> : (
              <table>
                <thead><tr><th>Farmer</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead>
                <tbody>
                  {applications.map(a => (
                    <tr key={a.id}>
                      <td>#{a.farmer_id}</td>
                      <td>{fmt(a.amount_requested)}</td>
                      <td><span className={`badge badge-${a.status === 'approved' ? 'green' : a.status === 'rejected' ? 'red' : 'amber'}`}>{a.status}</span></td>
                      <td>
                        {a.status === 'under_review' && (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button className="btn btn-primary btn-sm"
                              onClick={() => decide(a.id, 'approved', 'Approved by lender')}>
                              Approve
                            </button>
                            <button className="btn btn-danger btn-sm"
                              onClick={() => decide(a.id, 'rejected', 'Rejected by lender')}>
                              Reject
                            </button>
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

        {/* Passport View */}
        <div>
          {passportLoading && <div className="card" style={{ textAlign: 'center' }}><span className="spinner" /></div>}
          {selectedPassport && (
            <div>
              <div className="card" style={{ background: 'linear-gradient(135deg,#1a7c3a,#1b5e20)', color: 'white' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>Farmer #{selectedFarmer} — Trust Passport</div>
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>
                    {selectedPassport.overall_creditworthiness?.toFixed(0)}/100
                  </div>
                  <div style={{ opacity: 0.8 }}>Overall Creditworthiness</div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                  {[
                    ['Safe Credit Limit', fmt(selectedPassport.safe_credit_limit)],
                    ['Net Income', fmt(selectedPassport.expected_net_agricultural_income)],
                    ['Repayment Coverage', selectedPassport.repayment_coverage ? `${selectedPassport.repayment_coverage.toFixed(2)}x` : '—'],
                    ['Recommended Purpose', selectedPassport.recommended_credit_purpose],
                  ].map(([k, v]) => (
                    <div key={k} style={{ background: 'rgba(255,255,255,0.1)', borderRadius: 8, padding: 10 }}>
                      <div style={{ fontSize: '0.7rem', opacity: 0.75 }}>{k}</div>
                      <div style={{ fontWeight: 700 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="card-title">📊 Score Breakdown</div>
                {(selectedPassport.score_breakdown || []).map(b => (
                  <div key={b.component}>
                    <ScoreBar label={b.component} score={b.score} weight={b.weight} />
                    <p className="muted" style={{ fontSize: '0.78rem', marginBottom: 10 }}>{b.reason}</p>
                  </div>
                ))}
              </div>

              <div className="alert alert-amber" style={{ fontSize: '0.78rem' }}>
                ⚖️ This is an explainable agricultural credit profile. The lending decision is entirely yours. Market and benchmark data is DEMO/SYNTHETIC.
              </div>
            </div>
          )}
          {!selectedPassport && !passportLoading && (
            <div className="card"><p className="muted">Select a farmer to view their Trust Passport.</p></div>
          )}
        </div>
      </div>
    </div>
  );
}
