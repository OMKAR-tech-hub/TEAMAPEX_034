import { useState, useEffect } from 'react';
import { getMyPassport, generatePassport } from '../api';
import ScoreBar from '../components/ScoreBar';

function fmt(n) { return n ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'; }

export default function TrustPassport() {
  const [passport, setPassport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const { data } = await getMyPassport();
      setPassport(data);
    } catch { setPassport(null); }
    finally { setLoading(false); }
  }

  async function refresh() {
    setRefreshing(true);
    try {
      const { data } = await generatePassport();
      setPassport(data);
    } finally { setRefreshing(false); }
  }

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>;

  if (!passport) return (
    <div>
      <div className="page-title">Trust Passport</div>
      <div className="card">
        <p className="muted">No passport yet. Click below to generate your Trust Passport.</p>
        <button className="btn btn-primary mt-2" onClick={refresh}>Generate Passport</button>
      </div>
    </div>
  );

  const overall = passport.overall_creditworthiness || 0;
  const scoreColor = overall >= 75 ? '#4caf50' : overall >= 55 ? '#f59e0b' : '#ef5350';
  const breakdown = passport.score_breakdown || [];
  const exp = passport.explanation || {};
  const credit = exp.safe_credit_limit || {};
  const purpose = exp.credit_purpose || {};

  return (
    <div>
      <div className="flex-between mb-2">
        <div className="page-title">🌾 Farmer Trust Passport</div>
        <button className="btn btn-secondary btn-sm" onClick={refresh} disabled={refreshing}>
          {refreshing ? <><span className="spinner" /> Refreshing...</> : '🔄 Refresh'}
        </button>
      </div>

      {/* MAIN PASSPORT CARD */}
      <div className="passport-card">
        <div className="passport-header">
          <div>
            <div className="passport-name">Farmer Trust Passport</div>
            <div className="passport-subtitle">
              Portable Agricultural Economic Identity &nbsp;|&nbsp;
              v{passport.methodology_version} &nbsp;|&nbsp;
              Generated: {new Date(passport.generated_at).toLocaleDateString('en-IN')}
            </div>
          </div>
          <div className="passport-score-big">
            <div className="score-num" style={{ color: scoreColor }}>{overall.toFixed(0)}</div>
            <div className="score-label">Overall Creditworthiness / 100</div>
          </div>
        </div>

        <div className="score-grid">
          {breakdown.map(b => (
            <div className="score-item" key={b.component}>
              <div className="val">{b.score.toFixed(0)}</div>
              <div className="lbl">{b.component.replace(' Score', '')}</div>
            </div>
          ))}
        </div>

        <div className="credit-row">
          <div className="credit-box">
            <div className="cval">{fmt(passport.safe_credit_limit)}</div>
            <div className="clbl">Safe Credit Limit</div>
          </div>
          <div className="credit-box">
            <div className="cval">
              {passport.repayment_coverage ? `${passport.repayment_coverage.toFixed(2)}x` : '—'}
            </div>
            <div className="clbl">Repayment Coverage</div>
          </div>
          <div className="credit-box">
            <div className="cval">{fmt(passport.expected_net_agricultural_income)}</div>
            <div className="clbl">Expected Net Income</div>
          </div>
        </div>
      </div>

      {/* "Why this score?" */}
      <div className="card">
        <div className="card-title">📊 Score Breakdown</div>
        {breakdown.map(b => (
          <div key={b.component} style={{ marginBottom: 18 }}>
            <ScoreBar label={b.component} score={b.score} weight={b.weight} />
            <p className="muted" style={{ fontSize: '0.8rem', marginTop: 4, marginLeft: 2 }}>
              {b.reason}
            </p>
          </div>
        ))}
        <button className="btn btn-secondary btn-sm mt-1"
          onClick={() => setShowExplanation(v => !v)}>
          {showExplanation ? '▲ Hide Details' : '▼ Show Full Explanation'}
        </button>
        {showExplanation && (
          <pre style={{ fontSize: '0.72rem', marginTop: 12, background: '#f5f5f5', padding: 14, borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(exp, null, 2)}
          </pre>
        )}
      </div>

      {/* "How much can I safely borrow?" */}
      <div className="card">
        <div className="card-title">💰 How much can I safely borrow?</div>
        <div className="alert alert-info" style={{ marginBottom: 14 }}>
          Formula: <strong>Acreage × NHB Benchmark Yield × Conservative AGMARKNET Price × Risk Haircut</strong>
        </div>
        {credit.inputs && (
          <table>
            <tbody>
              <tr><td><strong>Acreage</strong></td><td>{credit.inputs.acreage} acres</td></tr>
              <tr><td><strong>NHB Benchmark Yield</strong></td><td>{credit.inputs.nhb_benchmark_yield_q_per_acre} quintals/acre</td></tr>
              <tr><td><strong>Conservative Market Price</strong></td><td>₹{credit.inputs.conservative_agmarknet_price_per_quintal}/quintal</td></tr>
              <tr><td><strong>Risk Haircut</strong></td><td>{credit.inputs.risk_haircut} ({credit.inputs.risk_haircut_description})</td></tr>
              <tr style={{ background: '#e8f5e9' }}>
                <td><strong>Safe Credit Limit</strong></td>
                <td><strong>{fmt(passport.safe_credit_limit)}</strong>
                  <span className="muted"> ({fmt(passport.safe_credit_limit_min)}–{fmt(passport.safe_credit_limit_max)} range)</span>
                </td>
              </tr>
            </tbody>
          </table>
        )}
        <p className="muted mt-1" style={{ fontSize: '0.78rem' }}>
          Data: {credit.data_sources?.benchmark} | {credit.data_sources?.market}
        </p>
      </div>

      {/* "What should this credit fund?" */}
      <div className="card">
        <div className="card-title">🌱 What should this credit fund?</div>
        <p style={{ fontWeight: 600, marginBottom: 8 }}>{passport.recommended_credit_purpose}</p>
        <p className="muted">{purpose.why}</p>
        <p className="muted mt-1" style={{ fontSize: '0.78rem' }}>{purpose.note}</p>
      </div>

      {/* Repayment */}
      <div className="card">
        <div className="card-title">📈 Repayment Capacity</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <p className="muted">Expected Revenue</p>
            <p style={{ fontWeight: 700, fontSize: '1.1rem' }}>{fmt(passport.expected_crop_revenue)}</p>
          </div>
          <div>
            <p className="muted">Cultivation Cost</p>
            <p style={{ fontWeight: 700, fontSize: '1.1rem' }}>{fmt(passport.estimated_cultivation_cost)}</p>
          </div>
          <div>
            <p className="muted">Net Agricultural Income</p>
            <p style={{ fontWeight: 700, fontSize: '1.1rem', color: '#1a7c3a' }}>{fmt(passport.expected_net_agricultural_income)}</p>
          </div>
          <div>
            <p className="muted">Repayment Coverage</p>
            <p style={{ fontWeight: 700, fontSize: '1.1rem' }}>
              {passport.repayment_coverage ? `${passport.repayment_coverage.toFixed(2)}x` : '—'}
            </p>
          </div>
        </div>
      </div>

      <div className="alert alert-amber" style={{ fontSize: '0.8rem' }}>
        ⚠️ <strong>Important:</strong> KisanSetu provides an explainable agricultural credit profile. The lender makes the final underwriting and approval decision. Market/benchmark data is from DEMO/SYNTHETIC dataset.
      </div>
    </div>
  );
}
