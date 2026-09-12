import { useState, useEffect } from 'react';
import { getMyProfile, getMyFarms, getMyProduction, getMySales, getMyPassport } from '../api';

function fmt(n) { return n ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'; }

export default function FarmerDashboard() {
  const [profile, setProfile] = useState(null);
  const [farms, setFarms] = useState([]);
  const [production, setProduction] = useState([]);
  const [sales, setSales] = useState([]);
  const [passport, setPassport] = useState(null);
  const role = localStorage.getItem('role');

  useEffect(() => {
    if (role === 'farmer') {
      getMyProfile().then(r => setProfile(r.data)).catch(() => {});
      getMyFarms().then(r => setFarms(r.data)).catch(() => {});
      getMyProduction().then(r => setProduction(r.data)).catch(() => {});
      getMySales().then(r => setSales(r.data)).catch(() => {});
      getMyPassport().then(r => setPassport(r.data)).catch(() => {});
    }
  }, [role]);

  if (role !== 'farmer') return (
    <div>
      <div className="page-title">Dashboard</div>
      <div className="card">
        <p>Use the sidebar to navigate to your section.</p>
      </div>
    </div>
  );

  const overall = passport?.overall_creditworthiness || 0;
  const scoreColor = overall >= 75 ? '#1a7c3a' : overall >= 55 ? '#f59e0b' : '#c62828';

  return (
    <div>
      <div className="page-title">🌾 Welcome, {profile?.name || 'Farmer'}</div>

      {/* Quick stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 20 }}>
        {[
          { label: 'Trust Score', value: overall.toFixed(0) + '/100', color: scoreColor },
          { label: 'Safe Credit Limit', value: fmt(passport?.safe_credit_limit) },
          { label: 'Total Farm Area', value: `${farms.reduce((a,f) => a + f.total_area_acres, 0).toFixed(1)} acres` },
          { label: 'FPO Verified Records', value: production.filter(p => p.fpo_verified).length + ' records' },
        ].map(s => (
          <div className="card" key={s.label} style={{ textAlign: 'center', padding: 18, marginBottom: 0 }}>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: s.color || '#1a7c3a' }}>{s.value}</div>
            <div className="muted" style={{ marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Profile */}
      {profile && (
        <div className="card">
          <div className="card-title">👤 Profile</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {[['Name', profile.name], ['District', profile.district], ['State', profile.state],
              ['Village', profile.village], ['Phone', profile.phone], ['Gender', profile.gender]
            ].map(([k, v]) => v ? (
              <div key={k}><span className="muted">{k}: </span><strong>{v}</strong></div>
            ) : null)}
          </div>
        </div>
      )}

      {/* Farms */}
      <div className="card">
        <div className="card-title">🏡 My Farms ({farms.length})</div>
        {farms.length === 0 ? <p className="muted">No farms registered yet.</p> : (
          <table>
            <thead><tr><th>Farm</th><th>Area (acres)</th><th>Soil</th><th>Irrigation</th><th>District</th></tr></thead>
            <tbody>
              {farms.map(f => (
                <tr key={f.id}>
                  <td>{f.farm_name}</td>
                  <td>{f.total_area_acres}</td>
                  <td>{f.soil_type || '—'}</td>
                  <td>{f.irrigation_type || '—'}</td>
                  <td>{f.district}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Production */}
      <div className="card">
        <div className="card-title">🌱 Production Records ({production.length})</div>
        {production.length === 0 ? <p className="muted">No records yet.</p> : (
          <table>
            <thead><tr><th>Crop</th><th>Season/Year</th><th>Quantity</th><th>Area</th><th>FPO Verified</th></tr></thead>
            <tbody>
              {production.slice(0,5).map(p => (
                <tr key={p.id}>
                  <td>{p.crop_type}</td>
                  <td>{p.season} {p.year}</td>
                  <td>{p.quantity} {p.unit}</td>
                  <td>{p.area_acres ? `${p.area_acres} ac` : '—'}</td>
                  <td>
                    <span className={`badge ${p.fpo_verified ? 'badge-green' : 'badge-amber'}`}>
                      {p.fpo_verified ? '✓ Verified' : 'Pending'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Sales */}
      <div className="card">
        <div className="card-title">💰 Sales Records ({sales.length})</div>
        {sales.length === 0 ? <p className="muted">No sales records yet.</p> : (
          <table>
            <thead><tr><th>Crop</th><th>Qty</th><th>Price/Q</th><th>Total</th><th>Market</th><th>Date</th></tr></thead>
            <tbody>
              {sales.slice(0,5).map(s => (
                <tr key={s.id}>
                  <td>{s.crop_name}</td>
                  <td>{s.quantity_sold}</td>
                  <td>₹{s.price_per_unit}</td>
                  <td>{fmt(s.total_amount)}</td>
                  <td>{s.market_name || '—'}</td>
                  <td>{new Date(s.sale_date).toLocaleDateString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
