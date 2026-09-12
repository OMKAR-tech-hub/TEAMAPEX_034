import { useEffect, useState } from 'react'
import api from '../api.js'

export default function FPODashboard() {
  const [farmers, setFarmers] = useState([])
  const [verifications, setVerifications] = useState([])
  const [form, setForm] = useState({ farmer_id: '', status: 'pending', integrity: false, notes: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [wallet, setWallet] = useState(null)
  const [loans, setLoans] = useState([])
  const [riskForm, setRiskForm] = useState({ loan_id: '', event_type: 'drought', severity: 'moderate' })
  const [vouchForm, setVouchForm] = useState({ farmer_id: '', guarantee_style: 'first_loss', notes: '' })
  const [vouches, setVouches] = useState([])

  const load = async () => {
    const [fRes, vRes, lRes] = await Promise.all([
      api.get('/farmers?limit=100'),
      api.get('/fpo/verifications'),
      api.get('/loans'),
    ])
    setFarmers(fRes.data)
    setVerifications(vRes.data)
    setLoans(lRes.data)
    api.get('/loans/wallet/me').then((r) => setWallet(r.data)).catch(() => {})
    api.get('/risk/vouches').then((r) => setVouches(r.data)).catch(() => {})
  }

  useEffect(() => {
    load().catch((e) => setError(e.response?.data?.detail || 'Failed to load'))
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.farmer_id) {
      setError('Select a farmer')
      return
    }
    try {
      await api.post('/fpo/verifications', {
        farmer_id: Number(form.farmer_id),
        verification_status: form.status,
        member_integrity_flag: form.integrity,
        notes: form.notes || null,
      })
      setMessage('Verification submitted')
      setForm({ farmer_id: '', status: 'pending', integrity: false, notes: '' })
      const vRes = await api.get('/fpo/verifications')
      setVerifications(vRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Submission failed')
    }
  }

  const submitVouch = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!vouchForm.farmer_id) {
      setError('Select a member farmer to vouch')
      return
    }
    try {
      const { data } = await api.post('/risk/vouches', {
        farmer_id: Number(vouchForm.farmer_id),
        guarantee_style: vouchForm.guarantee_style,
        notes: vouchForm.notes || null,
      })
      setMessage(`Vouch issued — ${data.effect}`)
      setVouchForm({ farmer_id: '', guarantee_style: 'first_loss', notes: '' })
      const vRes = await api.get('/risk/vouches')
      setVouches(vRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not issue vouch')
    }
  }

  const review = async (v, status) => {
    try {
      await api.put(`/fpo/verifications/${v.id}`, {
        verification_status: status,
        member_integrity_flag: status === 'verified',
      })
      const vRes = await api.get('/fpo/verifications')
      setVerifications(vRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Update failed')
    }
  }

  const declareRisk = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!riskForm.loan_id) {
      setError('Select a loan')
      return
    }
    try {
      await api.post(`/loans/${riskForm.loan_id}/risk-events`, {
        loan_id: Number(riskForm.loan_id),
        event_type: riskForm.event_type,
        severity: riskForm.severity,
      })
      setMessage('Risk event declared — tranches and calibrations updated')
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not declare risk event')
    }
  }

  const badge = (status) => {
    const map = {
      pending: 'bg-amber-100 text-amber-700',
      verified: 'bg-leaf-100 text-leaf-700',
      rejected: 'bg-red-100 text-red-700',
    }
    return `badge ${map[status] || 'bg-gray-100 text-gray-600'}`
  }

  const counts = verifications.reduce(
    (acc, v) => {
      acc[v.verification_status] = (acc[v.verification_status] || 0) + 1
      return acc
    },
    { pending: 0, verified: 0, rejected: 0 },
  )

  const statCard = (label, value, accent = 'text-gray-900') => (
    <div className="card p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${accent}`}>{value}</div>
    </div>
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">FPO Verification Desk</h1>
        <p className="text-sm text-gray-500">
          Verify member farmers and maintain member integrity flags.
        </p>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-sm text-red-600">
          {error}
        </div>
      )}
      {message && (
        <div className="mt-4 rounded-xl border border-leaf-100 bg-leaf-50 px-4 py-2.5 text-sm text-leaf-700">
          {message}
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statCard('Pending Review', counts.pending, 'text-amber-600')}
        {statCard('Verified', counts.verified, 'text-leaf-600')}
        {statCard(
          'Facilitation Wallet',
          wallet ? `₹${Number(wallet.wallet_balance).toLocaleString('en-IN')}` : '—',
          'text-emerald-600',
        )}
        {statCard('Total Members', verifications.length)}
      </div>

      {wallet && (
        <div className="mt-4 rounded-2xl border border-emerald-100 bg-gradient-to-r from-leaf-50 to-emerald-50 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">
                Value-chain facilitation credited to your wallet (2% of mandi sales, farmer pays ₹0)
              </div>
              <div className="text-2xl font-bold text-emerald-700">
                ₹{Number(wallet.wallet_balance).toLocaleString('en-IN')}
              </div>
            </div>
            <div className="text-right text-sm">
              <div className="text-xs text-gray-500">Lifetime facilitation tally</div>
              <div className="font-bold text-gray-900">
                ₹{Number(wallet.facilitation_tally).toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card h-fit p-6">
          <h2 className="text-lg font-semibold text-gray-900">Submit verification</h2>
          <form onSubmit={submit} className="mt-4 space-y-4">
            <div>
              <label className="field-label">Farmer</label>
              <select
                className="input-base"
                value={form.farmer_id}
                onChange={(e) => setForm({ ...form, farmer_id: e.target.value })}
              >
                <option value="">Select a farmer</option>
                {farmers.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} — {f.village} ({f.farmer_id})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label">Status</label>
              <select
                className="input-base"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="pending">Pending</option>
                <option value="verified">Verified</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded"
                checked={form.integrity}
                onChange={(e) => setForm({ ...form, integrity: e.target.checked })}
              />
              Member integrity confirmed
            </label>
            <div>
              <label className="field-label">Notes</label>
              <textarea
                className="input-base"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <button className="btn-primary w-full py-2.5">Submit verification</button>
          </form>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Verification log</h2>
            <span className="badge bg-amber-100 text-amber-700">{counts.pending} pending</span>
          </div>
          {verifications.length === 0 ? (
            <p className="mt-4 text-sm text-gray-500">No verifications yet.</p>
          ) : (
            <ul className="mt-4 max-h-[560px] space-y-3 overflow-auto pr-1">
              {verifications.map((v) => {
                const farmer = farmers.find((f) => f.id === v.farmer_id)
                return (
                  <li key={v.id} className="rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{farmer?.name ?? `Farmer #${v.farmer_id}`}</div>
                        <div className="text-xs text-gray-500">{v.fpo_name}</div>
                      </div>
                      <span className={badge(v.verification_status)}>{v.verification_status}</span>
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {v.notes || 'No notes'} · integrity:{' '}
                      {v.member_integrity_flag ? 'confirmed' : 'not confirmed'}
                    </div>
                    {v.verification_status === 'pending' && (
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={() => review(v, 'verified')}
                          className="rounded-lg bg-leaf-600 px-3 py-1 text-xs font-medium text-white hover:bg-leaf-700"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => review(v, 'rejected')}
                          className="rounded-lg border border-red-200 bg-red-50 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-100"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Community Vouch Desk</h2>
            <p className="mt-1 text-sm text-gray-500">
              Issue a first-loss style community guarantee for a member. An active vouch reduces the
              member's risk discount by 6 points and lowers their credit cost — this is how the
              community reduces lending risk (mission Q5).
            </p>
          </div>
          <span className="badge bg-emerald-100 text-emerald-700">
            {vouches.filter((v) => v.status === 'active').length} active vouches
          </span>
        </div>

        <form onSubmit={submitVouch} className="mt-4 grid gap-4 sm:grid-cols-4">
          <div>
            <label className="field-label">Member farmer</label>
            <select
              className="input-base"
              value={vouchForm.farmer_id}
              onChange={(e) => setVouchForm({ ...vouchForm, farmer_id: e.target.value })}
            >
              <option value="">Select a member</option>
              {farmers.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} — {f.farmer_id}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Guarantee style</label>
            <select
              className="input-base"
              value={vouchForm.guarantee_style}
              onChange={(e) => setVouchForm({ ...vouchForm, guarantee_style: e.target.value })}
            >
              <option value="first_loss">First-loss (community defers repayment first)</option>
              <option value="joint_review">Joint review (co-signed due diligence)</option>
            </select>
          </div>
          <div>
            <label className="field-label">Notes</label>
            <input
              className="input-base"
              placeholder="e.g. guarantee on input finance"
              value={vouchForm.notes}
              onChange={(e) => setVouchForm({ ...vouchForm, notes: e.target.value })}
            />
          </div>
          <div className="flex items-end">
            <button className="btn-primary w-full px-4 py-2">Issue vouch</button>
          </div>
        </form>

        {vouches.length > 0 && (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {vouches.map((v) => (
              <div key={v.id} className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-2.5 text-sm">
                <div>
                  <span className="font-medium text-gray-800">{v.farmer_ref || `Farmer #${v.farmer_id}`}</span>
                  <span className="ml-2 text-xs text-gray-400">{v.guarantee_style}</span>
                </div>
                <span className={`badge ${v.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                  {v.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Risk Event Desk</h2>
            <p className="mt-1 text-sm text-gray-500">
              Declare a field-level stress (drought, pest, flood…). Pending tranches are blocked,
              EMI pause safety net applies, and the farmer's Safe Credit Limit is recalibrated.
              The farmer is never charged.
            </p>
          </div>
          <span className="badge bg-red-50 text-red-600 normal-case">weather risk adapter</span>
        </div>

        <form onSubmit={declareRisk} className="mt-4 grid gap-4 sm:grid-cols-4">
          <div>
            <label className="field-label">Loan</label>
            <select
              className="input-base"
              value={riskForm.loan_id}
              onChange={(e) => setRiskForm({ ...riskForm, loan_id: e.target.value })}
            >
              <option value="">Select a loan</option>
              {loans.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.farmer_name} · {l.application_uid} · {l.status}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Event</label>
            <select
              className="input-base"
              value={riskForm.event_type}
              onChange={(e) => setRiskForm({ ...riskForm, event_type: e.target.value })}
            >
              {['drought', 'pest', 'flood', 'hail', 'disease'].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Severity</label>
            <select
              className="input-base"
              value={riskForm.severity}
              onChange={(e) => setRiskForm({ ...riskForm, severity: e.target.value })}
            >
              {['mild', 'moderate', 'severe'].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button className="btn-primary w-full px-4 py-2">Declare event</button>
          </div>
        </form>

        {loans.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {loans.map((l) => (
              <span key={l.id} className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600">
                {l.application_uid} · {l.farmer_name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}