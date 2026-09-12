import { useState } from 'react';
import { whatIfSimulation } from '../api';

function fmt(n) { return n != null ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'; }

export default function WhatIf() {
  const [form, setForm] = useState({
    hypothetical_crop: 'wheat',
    hypothetical_area_acres: 5,
    hypothetical_price_per_quintal: 2150,
    hypothetical_yield_quintals_per_acre: 16,
    hypothetical_cultivation_cost: 75000,
    requested_loan_amount: 100000,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function update(k, v) { setForm(f => ({ ...f, [k]: parseFloat(v) || v })); }

  async function simulate() {
    setLoading(true); setError('');
    try {
      const { data } = await whatIfSimulation(form);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed');
    } finally { setLoading(false); }
  }

  const sliders = [
    { key: 'hypothetical_area_acres',             label: 'Acreage (acres)',              min: 0.5, max: 20, step: 0.5 },
    { key: 'hypothetical_yield_quintals_per_acre', label: 'Yield (quintals/acre)',        min: 2,   max: 50, step: 1 },
    { key: 'hypothetical_price_per_quintal',        label: 'Price per quintal (₹)',       min: 500, max: 10000, step: 50 },
    { key: 'hypothetical_cultivation_cost',         label: 'Cultivation Cost (₹ total)', min: 5000, max: 300000, step: 5000 },
    { key: 'requested_loan_amount',                 label: 'Requested Loan (₹)',          min: 5000, max: 500000, step: 5000 },
  ];

  return (
    <div>
      <div className="page-title">🔮 What-If Credit Simulator</div>
      <div className="alert alert-info" style={{ marginBottom: 16 }}>
        Simulate how your assessment changes with different inputs. <strong>Your real data is never modified.</strong>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="card">
          <div className="card-title">⚙️ Adjust Parameters</div>
          <div className="form-group">
            <label>Crop</label>
            <select value={form.hypothetical_crop} onChange={e => update('hypothetical_crop', e.target.value)}>
              {['wheat','rice','soybean','cotton','maize'].map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          {sliders.map(s => (
            <div className="slider-group" key={s.key}>
              <div className="slider-label">
                <span>{s.label}</span>
                <strong>{s.key.includes('price') || s.key.includes('cost') || s.key.includes('loan')
                  ? fmt(form[s.key]) : form[s.key]}</strong>
              </div>
              <input type="range" min={s.min} max={s.max} step={s.step}
                value={form[s.key]}
                onChange={e => update(s.key, e.target.value)} />
            </div>
          ))}
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={simulate} disabled={loading}>
            {loading ? <><span className="spinner" /> Simulating...</> : '▶ Run Simulation'}
          </button>
          {error && <div className="alert alert-error mt-1">{error}</div>}
        </div>

        <div>
          {result ? (
            <>
              <div className="card">
                <div className="card-title">📊 Hypothetical Results</div>
                <table>
                  <tbody>
                    {[
                      ['Crop', result.hypothetical.crop],
                      ['Area', `${result.hypothetical.area_acres} acres`],
                      ['Expected Production', `${result.hypothetical.expected_production_quintals} Q`],
                      ['Expected Revenue', fmt(result.hypothetical.expected_revenue)],
                      ['Cultivation Cost', fmt(result.hypothetical.cultivation_cost)],
                      ['Net Income', fmt(result.hypothetical.net_income)],
                      ['Repayment Coverage', result.hypothetical.repayment_coverage ? `${result.hypothetical.repayment_coverage}x` : '—'],
                      ['Safe Credit Limit', fmt(result.hypothetical.safe_credit_limit)],
                      ['Requested Loan', fmt(result.hypothetical.requested_loan)],
                    ].map(([k, v]) => <tr key={k}><td className="muted">{k}</td><td><strong>{v}</strong></td></tr>)}
                  </tbody>
                </table>
                {result.hypothetical.within_safe_limit !== null && (
                  <div className={`alert ${result.hypothetical.within_safe_limit ? 'alert-success' : 'alert-error'} mt-1`}>
                    {result.hypothetical.within_safe_limit
                      ? '✓ Requested loan is within the safe credit limit'
                      : '✗ Requested loan exceeds the safe credit limit'}
                  </div>
                )}
              </div>

              <div className="card">
                <div className="card-title">↔ Change vs Current</div>
                {[
                  ['Revenue Change', result.delta.revenue_change],
                  ['Net Income Change', result.delta.net_income_change],
                  ['Safe Limit Change', result.delta.safe_limit_change],
                ].map(([k, v]) => (
                  <div key={k} style={{ marginBottom: 10 }}>
                    <span className="muted">{k}: </span>
                    <strong style={{ color: v >= 0 ? '#1a7c3a' : '#c62828' }}>
                      {v >= 0 ? '+' : ''}{fmt(v)}
                    </strong>
                  </div>
                ))}
                <p className="muted" style={{ fontSize: '0.78rem', marginTop: 8 }}>{result.note}</p>
              </div>
            </>
          ) : (
            <div className="card">
              <p className="muted">Adjust parameters and click Run Simulation to see results.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
