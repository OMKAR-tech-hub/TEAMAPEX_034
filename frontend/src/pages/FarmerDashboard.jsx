import { useEffect, useState } from 'react'
import api from '../api.js'
import { useAuth } from '../context/AuthContext.jsx'
import ScoreBar from '../components/ScoreBar.jsx'

const ATTR_OPTIONS = [
  { key: 'name', label: 'Name' },
  { key: 'mobile', label: 'Mobile number' },
  { key: 'village', label: 'Village' },
  { key: 'district', label: 'District' },
  { key: 'acreage', label: 'Acreage' },
  { key: 'crop', label: 'Crop' },
  { key: 'passport', label: 'Passport score' },
]

export default function FarmerDashboard() {
  const { user } = useAuth()
  const [farmer, setFarmer] = useState(null)
  const [passport, setPassport] = useState(null)
  const [computing, setComputing] = useState(false)
  const [banks, setBanks] = useState([])
  const [consents, setConsents] = useState([])
  const [grant, setGrant] = useState({ bank_user_id: '', attributes: ['name', 'passport'], masked: [] })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [uw, setUw] = useState({ requested_amount: '100000', tenure_months: '10', annual_interest_rate: '0.11', purpose_category: 'working_capital' })
  const [uwBusy, setUwBusy] = useState(false)
  const [uwResult, setUwResult] = useState(null)
  const [loans, setLoans] = useState([])
  const [loanBusy, setLoanBusy] = useState(0)
  const [settle, setSettle] = useState({ loan_id: '', sale_value: '', crop: 'paddy' })
  const [assessment, setAssessment] = useState(null)
  const [assessing, setAssessing] = useState(false)
  const [sources, setSources] = useState([])
  const [ins, setIns] = useState({ enabled: false, sum_class: '' })
  const [prod, setProd] = useState({ crop: 'paddy', quantity: '', year: '', distressed: false })
  const [purposes, setPurposes] = useState([])
  const [openQ, setOpenQ] = useState(null)

  const load = async () => {
    const me = await api.get('/auth/me')
    const farmerId = me.data.farmer_id
    const [fRes, pRes, bRes, cRes, sRes, uRes] = await Promise.all([
      api.get(`/farmers/${farmerId}`),
      api.get(`/passports/${farmerId}`).catch((e) => {
        if (e.response?.status === 404) return null
        throw e
      }),
      api.get('/auth/banks'),
      api.get('/consents'),
      api.get('/risk/sources'),
      api.get(`/risk/${farmerId}/latest`).catch((e) => {
        if (e.response?.status === 404) return null
        throw e
      }),
    ])
    setFarmer(fRes.data)
    setPassport(pRes?.data ?? null)
    setBanks(bRes.data)
    setConsents(cRes.data)
    setSources(sRes.data?.sources ?? [])
    setAssessment(uRes?.data ?? null)
    setProd((p) => ({ ...p, crop: fRes.data?.primary_crop || 'paddy' }))
    const pur = await api.get('/risk/purposes').catch(() => null)
    setPurposes(pur?.data?.purposes ?? [])
  }

  const reloadLoans = async () => {
    const lRes = await api.get('/loans')
    setLoans(lRes.data)
  }

  useEffect(() => {
    load()
      .then(reloadLoans)
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load dashboard'))
  }, [user])

  const compute = async () => {
    setComputing(true)
    setMessage('')
    try {
      const { data } = await api.post(`/passports/compute/${farmer.farmer_id}`, { force_recompute: true })
      setPassport(data.passport)
      setMessage('Passport recomputed from the deterministic credit engine')
    } catch (e) {
      setError(e.response?.data?.detail || 'Computation failed')
    } finally {
      setComputing(false)
    }
  }

  const toggleAttribute = (key) => {
    setGrant((g) => ({
      ...g,
      attributes: g.attributes.includes(key)
        ? g.attributes.filter((a) => a !== key)
        : [...g.attributes, key],
    }))
  }

  const submitConsent = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!grant.bank_user_id) {
      setError('Select a bank')
      return
    }
    try {
      await api.post('/consents', {
        bank_user_id: Number(grant.bank_user_id),
        attributes: grant.attributes,
        masked_attributes: grant.masked,
      })
      setMessage('Consent granted; bank visibility updated')
      setGrant({ ...grant, bank_user_id: '' })
      const cRes = await api.get('/consents')
      setConsents(cRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not grant consent')
    }
  }

  const toggleConsent = async (consent) => {
    try {
      await api.put(`/consents/${consent.id}`, { granted: !consent.granted })
      const cRes = await api.get('/consents')
      setConsents(cRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update consent')
    }
  }

  const runUnderwrite = async (e) => {
    e.preventDefault()
    setUwBusy(true)
    setUwResult(null)
    setError('')
    try {
      const { data } = await api.post('/underwrite/evaluate', {
        farmer_id: farmer.farmer_id,
        requested_amount: parseFloat(uw.requested_amount),
        tenure_months: parseInt(uw.tenure_months, 10),
        annual_interest_rate: parseFloat(uw.annual_interest_rate),
        purpose_category: uw.purpose_category,
      })
      setUwResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Underwrite evaluation failed')
    } finally {
      setUwBusy(false)
    }
  }

  const runAssessment = async () => {
    setAssessing(true)
    setError('')
    try {
      const { data } = await api.post(`/risk/assess/${farmer.farmer_id}`)
      setAssessment(data)
      setMessage('Agri-risk assessment refreshed — range and reasons recomputed')
      setIns({ enabled: data.insurance_uplift > 0, sum_class: '' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Assessment failed')
    } finally {
      setAssessing(false)
    }
  }

  const saveInsurance = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(`/risk/${farmer.farmer_id}/insurance`, {
        crop_insured: ins.enabled,
        insurance_sum_assured: ins.sum_class ? parseFloat(ins.sum_class) : null,
      })
      setMessage(ins.enabled ? 'Crop insurance recorded — risk uplift applied' : 'Insurance removed')
      await runAssessment()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save insurance')
    }
  }

  const addProduction = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(`/risk/${farmer.farmer_id}/production-records`, {
        crop_type: prod.crop,
        quantity: parseFloat(prod.quantity),
        season: 'Kharif',
        year: parseInt(prod.year, 10),
        verified: true,
        weather_distress_observed: prod.distressed,
      })
      setMessage('Production record added — yield stability factor updated')
      setProd({ ...prod, quantity: '', year: '' })
      await runAssessment()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not add production record')
    }
  }

  const requestLoan = async () => {
    if (!uwResult || uwResult.decision !== 'approved') {
      setError('Run underwrite and get an approved decision first')
      return
    }
    setLoanBusy((n) => n + 1)
    setError('')
    try {
      const { data } = await api.post('/loans', {
        principal: uwResult.requested_amount,
        tenure_months: uwResult.amortization.tenure_months,
        annual_interest_rate: uwResult.inputs.annual_interest_rate,
        purpose_category: uwResult.purpose?.category || 'working_capital',
        purpose_note: uwResult.purpose?.note || null,
      })
      setMessage(`Loan ${data.application_uid} raised — PSL: ${data.psl_category}`)
      await reloadLoans()
      setSettle((s) => ({ ...s, loan_id: String(data.id) }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not raise loan')
    } finally {
      setLoanBusy((n) => n - 1)
    }
  }

  const settleSale = async (e) => {
    e.preventDefault()
    setLoanBusy((n) => n + 1)
    setError('')
    try {
      await api.post('/settlements', {
        loan_id: Number(settle.loan_id),
        sale_value: parseFloat(settle.sale_value),
        crop: settle.crop,
      })
      setMessage('Mandi sale settled — escrow split computed')
      await reloadLoans()
    } catch (err) {
      setError(err.response?.data?.detail || 'Settlement failed')
    } finally {
      setLoanBusy((n) => n - 1)
    }
  }

  const inr = (v) => (v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`)

  const statusBadge = (status) => {
    const map = {
      underwritten: 'bg-sky-100 text-sky-700',
      approved: 'bg-indigo-100 text-indigo-700',
      disbursing: 'bg-leaf-100 text-leaf-700',
      active: 'bg-amber-100 text-amber-700',
      repaid: 'bg-leaf-100 text-leaf-700',
    }
    return `badge ${map[status] || 'bg-gray-100 text-gray-600'}`
  }

  const field = (label, value) => (
    <div className="flex justify-between border-b border-gray-100 py-2 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-semibold text-gray-900">{value}</span>
    </div>
  )

  const activeConsents = consents.filter((c) => c.granted).length
  const overallScore = passport?.component_scores
    ? Math.round(
        Object.values(passport.component_scores).reduce((a, b) => a + b, 0) /
          Object.values(passport.component_scores).length,
      )
    : null

  const statCard = (label, value, sub, accent = 'text-leaf-700') => (
    <div className="card p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-gray-500">{sub}</div>}
    </div>
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Farmer Passport</h1>
          <p className="text-sm text-gray-500">
            Your verified agricultural identity and credit worthiness.
          </p>
        </div>
        {farmer && (
          <div className="rounded-xl border border-leaf-100 bg-leaf-50 px-4 py-2 text-sm">
            <div className="font-semibold text-leaf-700">{farmer.name}</div>
            <div className="text-xs text-gray-500">
              {farmer.crop_season} · {farmer.village}
            </div>
          </div>
        )}
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
        {statCard(
          'Safe Credit Limit',
          passport ? `₹${Number(passport.safe_credit_limit).toLocaleString('en-IN')}` : '—',
          passport ? 'what banks can pre-assess' : 'compute your passport',
        )}
        {statCard('Credit Tier', passport ? passport.credit_tier : '—', passport ? 'engine classification' : '', 'text-amber-600')}
        {statCard(
          'Repayment Coverage',
          passport ? (passport.repayment_coverage === null ? 'No debt' : `${passport.repayment_coverage}x`) : '—',
          'income vs repayment demand',
          'text-sky-600',
        )}
        {statCard('Active Consents', activeConsents, 'lenders currently sharing your data', 'text-rose-600')}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900">Identity</h2>
          {farmer && (
            <div className="mt-4">
              {field('Name', farmer.name)}
              {field('Mobile', farmer.mobile)}
              {field('Village', farmer.village)}
              {field('District', farmer.district)}
              {field('State', farmer.state)}
              {field('Acreage', `${farmer.acreage} acres`)}
              {field('Primary crop', farmer.primary_crop || '—')}
              {field('FPO membership', farmer.fpo_membership || '—')}
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Trust Passport Score</h2>
            {overallScore !== null && (
              <div className="flex items-center gap-2 rounded-full bg-leaf-50 px-3 py-1">
                <span className="text-xs font-medium text-gray-500">Overall</span>
                <span className="text-sm font-bold text-leaf-700">{overallScore}/100</span>
              </div>
            )}
          </div>

          {passport ? (
            <>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <ScoreBar label="Identity" value={passport.component_scores.identity} />
                <ScoreBar label="Landholding" value={passport.component_scores.landholding} />
                <ScoreBar label="Production" value={passport.component_scores.production} />
                <ScoreBar label="FPO verification" value={passport.component_scores.verification} />
                <ScoreBar label="Repayment" value={passport.component_scores.repayment} />
                <ScoreBar label="Stability" value={passport.component_scores.stability} />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 rounded-2xl bg-gradient-to-br from-leaf-50 to-emerald-50 p-4 text-center text-sm">
                <div>
                  <div className="font-bold text-gray-900">{passport.credit_tier}</div>
                  <div className="text-xs text-gray-500">Credit tier</div>
                </div>
                <div>
                  <div className="font-bold text-gray-900">
                    {passport.repayment_coverage === null
                      ? 'No debt'
                      : `${passport.repayment_coverage}x`}
                  </div>
                  <div className="text-xs text-gray-500">Coverage</div>
                </div>
                <div>
                  <div className="font-bold text-gray-900">
                    {(passport.risk_haircut * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">Risk haircut</div>
                </div>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-700">
              Your Trust Passport has not been computed yet. Compute it with the button below.
            </div>
          )}

          <button
            onClick={compute}
            disabled={computing || !farmer}
            className="btn-primary w-full py-2.5"
          >
            {computing ? 'Computing...' : passport ? 'Recompute score' : 'Compute score'}
          </button>
        </div>
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Agri-Risk & Credit Range</h2>
            <p className="mt-1 text-sm text-gray-500">
              Explainable agricultural-risk engine: production stability, market price, crop
              condition, community trust and debt repayment drive your safe credit range.
            </p>
          </div>
          <button onClick={runAssessment} disabled={assessing || !farmer} className="btn-primary px-4 py-2">
            {assessing ? 'Assessing...' : assessment ? 'Re-assess' : 'Run assessment'}
          </button>
        </div>

        {!assessment ? (
          <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-700">
            No assessment yet. Run the risk engine to see your credit range and the reasons behind it.
          </div>
        ) : (
          <div className="mt-5 grid gap-6 lg:grid-cols-2">
            <div>
              <div className="flex items-center gap-3">
                <span
                  className={`badge text-base ${
                    assessment.risk_tier === 'low'
                      ? 'bg-leaf-100 text-leaf-700'
                      : assessment.risk_tier === 'medium'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-red-100 text-red-700'
                  }`}
                >
                  {assessment.risk_tier.toUpperCase()} RISK · {assessment.risk_score}
                </span>
                {assessment.community_vouch && (
                  <span className="badge bg-emerald-100 text-emerald-700">FPO community vouch active</span>
                )}
                {assessment.insurance_uplift > 0 && (
                  <span className="badge bg-sky-100 text-sky-700">
                    insurance +{Math.round(assessment.insurance_uplift * 100)}%
                  </span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3 rounded-2xl bg-gradient-to-br from-amber-50 to-leaf-50 p-4 text-center">
                <div>
                  <div className="font-bold text-gray-900">₹{Number(assessment.range_low).toLocaleString('en-IN')}</div>
                  <div className="text-xs text-gray-500">range low</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-leaf-700">₹{Number(assessment.recommended_credit).toLocaleString('en-IN')}</div>
                  <div className="text-xs text-gray-500">recommended credit</div>
                </div>
                <div>
                  <div className="font-bold text-gray-900">₹{Number(assessment.range_high).toLocaleString('en-IN')}</div>
                  <div className="text-xs text-gray-500">range high</div>
                </div>
              </div>

              <div className="mt-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">Why this range</div>
                <ul className="mt-2 space-y-2">
                  {assessment.top_reasons.map((t) => (
                    <li key={t.factor} className="rounded-xl border border-gray-100 bg-white/70 px-3 py-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium capitalize text-gray-700">{t.factor.replace(/_/g, ' ')}</span>
                        <span className="text-xs text-gray-400">impact {t.impact_pct}%</span>
                      </div>
                      <p className="mt-0.5 text-xs leading-relaxed text-gray-500">{t.reason}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">Factor scores (higher = riskier)</div>
                <div className="mt-2 rounded-xl border border-gray-100 px-4 py-2">
                  {Object.entries(assessment.factor_scores).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between gap-2 border-b border-gray-100 py-2 text-sm last:border-0">
                      <span className="capitalize text-gray-500">{k.replace(/_/g, ' ')}</span>
                      <span className="font-bold text-gray-900">{v}<span className="text-xs font-normal text-gray-400">/100</span></span>
                    </div>
                  ))}
                </div>
              </div>

              <form onSubmit={saveInsurance} className="rounded-xl border border-sky-100 bg-sky-50/60 p-4">
                <div className="text-sm font-semibold text-gray-800">Crop insurance (risk-transfer mitigant)</div>
                <div className="mt-3 flex flex-wrap items-end gap-3">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded"
                      checked={ins.enabled}
                      onChange={(e) => setIns({ ...ins, enabled: e.target.checked })}
                    />
                    Insured this season
                  </label>
                  <input
                    type="number"
                    min="0"
                    placeholder="Sum assured (₹)"
                    className="input-base flex-1"
                    value={ins.sum_class}
                    onChange={(e) => setIns({ ...ins, sum_class: e.target.value })}
                  />
                  <button className="btn-primary px-4 py-2">{ins.enabled ? 'Record' : 'Update'}</button>
                </div>
              </form>

              <form onSubmit={addProduction} className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
                <div className="text-sm font-semibold text-gray-800">Add verified production record</div>
                <div className="mt-3 grid gap-3 sm:grid-cols-4">
                  <input className="input-base" value={prod.crop} onChange={(e) => setProd({ ...prod, crop: e.target.value })} />
                  <input type="number" min="1" placeholder="Quantity (q)" className="input-base" value={prod.quantity} onChange={(e) => setProd({ ...prod, quantity: e.target.value })} required />
                  <input type="number" min="2020" max="2027" placeholder="Year" className="input-base" value={prod.year} onChange={(e) => setProd({ ...prod, year: e.target.value })} required />
                  <button className="btn-primary px-4 py-2">Add record</button>
                </div>
                <label className="mt-2 flex items-center gap-2 text-sm text-gray-600">
                  <input type="checkbox" className="h-4 w-4 rounded" checked={prod.distressed} onChange={(e) => setProd({ ...prod, distressed: e.target.checked })} />
                  Season had weather distress observed
                </label>
              </form>
            </div>
          </div>
        )}

        {assessment && assessment.mission_answers && (
          <div className="mt-6 border-t border-gray-100 pt-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              The six lending questions, answered from your data
            </div>
            <div className="mt-3 grid gap-2">
              {assessment.mission_answers.map((qa, i) => (
                <div key={i} className="rounded-xl border border-gray-100">
                  <button
                    type="button"
                    onClick={() => setOpenQ(openQ === i ? null : i)}
                    className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm font-medium text-gray-800"
                  >
                    <span>{qa.question}</span>
                    <span className="text-gray-400">{openQ === i ? '−' : '+'}</span>
                  </button>
                  {openQ === i && (
                    <div className="border-t border-gray-100 px-4 py-3 text-sm">
                      <p className="text-gray-700">{qa.answer}</p>
                      <p className="mt-1.5 text-xs italic text-gray-400">evidence · {qa.evidence}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="card mt-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Consent for banks</h2>
            <p className="mt-1 text-sm text-gray-500">
              Grant banks access to specific attributes. Masking keeps fields hidden from the bank.
            </p>
          </div>
          <span className="badge bg-leaf-100 text-leaf-700">{activeConsents} active</span>
        </div>

        <form onSubmit={submitConsent} className="mt-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">Select bank</label>
              <select
                className="input-base"
                value={grant.bank_user_id}
                onChange={(e) => setGrant({ ...grant, bank_user_id: e.target.value })}
              >
                <option value="">Choose a bank</option>
                {banks.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button className="btn-primary w-full">Grant consent</button>
            </div>
          </div>

          <div>
            <span className="field-label">Attributes to share · <span className="text-sky-600">mask toggle</span></span>
            <div className="flex flex-wrap gap-2">
              {ATTR_OPTIONS.map((a) => {
                const checked = grant.attributes.includes(a.key)
                const masked = grant.masked.includes(a.key)
                return (
                  <label
                    key={a.key}
                    className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                      checked
                        ? masked
                          ? 'border-sky-300 bg-sky-50 text-sky-800'
                          : 'border-leaf-600 bg-leaf-50 text-leaf-800'
                        : 'border-gray-300 bg-white'
                    }`}
                  >
                    <input type="checkbox" className="h-4 w-4" checked={checked} onChange={() => toggleAttribute(a.key)} />
                    {a.label}
                    <button
                      type="button"
                      title={masked ? 'Unmask' : 'Mask this attribute'}
                      onClick={(e) => {
                        e.preventDefault()
                        setGrant((g) => ({
                          ...g,
                          attributes: g.attributes.includes(a.key) ? g.attributes : [...g.attributes, a.key],
                          masked: masked
                            ? g.masked.filter((m) => m !== a.key)
                            : [...g.masked, a.key],
                        }))
                      }}
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        masked ? 'bg-sky-500 text-white' : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                      }`}
                    >
                      {masked ? 'Masked' : 'Mask'}
                    </button>
                  </label>
                )
              })}
            </div>
          </div>
        </form>

        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-600">Active grants</h3>
          {consents.length === 0 ? (
            <p className="mt-2 text-sm text-gray-500">No consent grants yet.</p>
          ) : (
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {consents.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3"
                >
                  <div>
                    <div className="font-medium">{c.bank_name}</div>
                    <div className="text-xs text-gray-500">
                      {c.attributes.join(', ') || 'none'}
                      {c.masked_attributes.length > 0 &&
                        ` · masked: ${c.masked_attributes.join(', ')}`}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleConsent(c)}
                    className={`rounded-lg px-3 py-1 text-sm font-medium ${
                      c.granted ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-leaf-50 text-leaf-700 hover:bg-leaf-100'
                    }`}
                  >
                    {c.granted ? 'Revoke' : 'Re-grant'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Your data, your ownership</h2>
            <p className="mt-1 text-sm text-gray-500">
              Every credit figure on this dashboard is computed from the sources below. Nothing is
              sold — lenders only see what you grant, and you can revoke anytime.
            </p>
          </div>
          <span className="badge bg-leaf-100 text-leaf-700">Q6 · data ownership</span>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {(sources.length ? sources : []).map((s) => (
            <div key={s.key} className="rounded-xl border border-gray-100 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-800">{s.name}</span>
                <span className="badge bg-gray-100 text-gray-600 normal-case">{s.ownership}</span>
              </div>
              <div className="mt-1 text-xs text-gray-500">
                {s.consent_required ? 'Consent-gated · revocable' : s.provenance || 'Full ownership'}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Loan Underwrite</h2>
            <p className="mt-1 text-sm text-gray-500">
              Evaluate a loan request against your Safe Credit Limit. The origination fee is
              paid by the lender — never charged to you (RBI DLG).
            </p>
          </div>
          {uwResult && (
            <span
              className={`badge ${
                uwResult.decision === 'approved'
                  ? 'bg-leaf-100 text-leaf-700'
                  : uwResult.decision === 'adjust'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-600'
              }`}
            >
              {uwResult.decision.toUpperCase()}
            </span>
          )}
        </div>

        <form onSubmit={runUnderwrite} className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="field-label">Loan amount (₹)</label>
            <input
              type="number"
              min="1000"
              step="1000"
              className="input-base"
              value={uw.requested_amount}
              onChange={(e) => setUw({ ...uw, requested_amount: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="field-label">Tenure (months)</label>
            <input
              type="number"
              min="3"
              max="60"
              className="input-base"
              value={uw.tenure_months}
              onChange={(e) => setUw({ ...uw, tenure_months: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="field-label">Interest rate (p.a.)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="0.30"
              className="input-base"
              value={uw.annual_interest_rate}
              onChange={(e) => setUw({ ...uw, annual_interest_rate: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="field-label">Purpose of loan</label>
            <select
              className="input-base"
              value={uw.purpose_category}
              onChange={(e) => setUw({ ...uw, purpose_category: e.target.value })}
            >
              {(purposes.length ? purposes : [{ category: 'working_capital' }]).map((p) => (
                <option key={p.category} value={p.category}>
                  {p.category.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button disabled={uwBusy || !farmer} className="btn-primary w-full py-2">
              {uwBusy ? 'Evaluating...' : 'Evaluate'}
            </button>
          </div>
        </form>

        {uwResult && (
          <div className="mt-5 grid gap-4 rounded-2xl border border-gray-100 bg-gray-50/60 p-4 sm:grid-cols-4">
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Safe limit</div>
              <div className="mt-0.5 text-lg font-bold text-leaf-700">
                ₹{Number(uwResult.safe_credit_limit).toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Defensible range</div>
              <div className="mt-0.5 text-lg font-bold text-gray-900">
                ₹{Number(uwResult.safe_credit_range.low).toLocaleString('en-IN')}
                {' – '}
                ₹{Number(uwResult.safe_credit_range.high).toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Agri-risk tier</div>
              <div className="mt-0.5 text-lg font-bold text-amber-600 capitalize">
                {uwResult.agri_risk.tier}
                {uwResult.agri_risk.community_vouch && (
                  <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold normal-case text-emerald-700">
                    FPO vouch
                  </span>
                )}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Purpose steering</div>
              <div className="mt-0.5 text-lg font-bold text-gray-900 capitalize">
                {uwResult.purpose.category.replace(/_/g, ' ')}
                <span className="ml-2 text-xs font-semibold text-gray-500">
                  x{uwResult.purpose.alignment}
                </span>
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Monthly EMI</div>
              <div className="mt-0.5 text-lg font-bold text-gray-900">
                ₹{Number(uwResult.amortization.monthly_emi).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Total interest</div>
              <div className="mt-0.5 text-lg font-bold text-gray-900">
                ₹{Number(uwResult.amortization.interest_payable).toLocaleString('en-IN')}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Repayment coverage</div>
              <div className="mt-0.5 text-lg font-bold text-sky-600">
                {uwResult.repayment_coverage === null ? '—' : `${uwResult.repayment_coverage}x`}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Risk haircut</div>
              <div className="mt-0.5 text-lg font-bold text-gray-900">
                {Math.round(uwResult.risk_haircut * 100)}%
              </div>
            </div>
            <div className="rounded-xl bg-white px-4 py-3 text-sm sm:col-span-4">
              <div className="flex items-center justify-between text-gray-600">
                <span>Underwriter decision</span>
                <span className="font-semibold">{uwResult.reason}</span>
              </div>
              <div className="mt-2 flex items-center justify-between text-gray-600">
                <span>
                  Origination fee ({Math.round(uwResult.origination_fee.rate * 10000) / 100}%) — paid by {uwResult.origination_fee.payer}
                </span>
                <span className="font-semibold">
                  ₹{Number(uwResult.origination_fee.amount).toLocaleString('en-IN')}
                  <span className="ml-2 text-xs text-leaf-600">farmer charged ₹0</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Loans & Repayment</h2>
            <p className="mt-1 text-sm text-gray-500">
              Raise a loan against your approved underwrite. Tranching, escrow settlements and
              your repayment tracker are shown below.
            </p>
          </div>
          <button
            onClick={requestLoan}
            disabled={loanBusy > 0}
            className="btn-primary px-4 py-2 disabled:opacity-50"
          >
            Raise {uwResult ? `₹${Number(uwResult.requested_amount).toLocaleString('en-IN')}` : 'loan'}
          </button>
        </div>

        {loans.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">
            No loans yet. Run an underwrite and get an <span className="font-semibold">approved</span>{' '}
            decision, then raise a loan.
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {loans.map((loan) => {
              const active = loan.status !== 'repaid'
              return (
                <div key={loan.id} className="rounded-2xl border border-gray-200 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div>
                        <div className="font-semibold text-gray-900">{loan.application_uid}</div>
                        <div className="text-xs text-gray-500">{loan.psl_category}</div>
                        <div className="mt-1 flex items-center gap-2">
                          <span className="badge bg-indigo-50 text-indigo-700 normal-case">
                            {loan.purpose_category?.replace(/_/g, ' ') || 'working capital'}
                          </span>
                          {loan.purpose_note && <span className="text-[11px] italic text-gray-400">{loan.purpose_note}</span>}
                        </div>
                      </div>
                      <span className={statusBadge(loan.status)}>{loan.status}</span>
                    </div>
                    <div className="text-right text-sm">
                      <div className="text-lg font-bold text-gray-900">{inr(loan.principal)}</div>
                      <div className="text-xs text-gray-500">
                        EMI {loan.monthly_emi != null ? `₹${Number(loan.monthly_emi).toLocaleString('en-IN')}` : '—'}
                        /mo · {loan.tenure_months} months
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-4">
                    <div className="rounded-xl bg-gray-50 px-4 py-3">
                      <div className="text-xs text-gray-500">Disbursed</div>
                      <div className="font-bold text-gray-900">{inr(loan.amount_disbursed)}</div>
                    </div>
                    <div className="rounded-xl bg-gray-50 px-4 py-3">
                      <div className="text-xs text-gray-500">Outstanding</div>
                      <div className="font-bold text-amber-600">{inr(loan.outstanding)}</div>
                    </div>
                    <div className="rounded-xl bg-gray-50 px-4 py-3">
                      <div className="text-xs text-gray-500">Total payable</div>
                      <div className="font-bold text-gray-900">{inr(loan.total_payable)}</div>
                    </div>
                    <div className="rounded-xl bg-gray-50 px-4 py-3">
                      <div className="text-xs text-gray-500">Progress</div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-leaf-700">{loan.repayment_progress}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-2 rounded-full bg-leaf-600 transition-all"
                      style={{ width: `${Math.min(100, loan.repayment_progress)}%` }}
                    />
                  </div>

                  <div className="mt-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Disbursement tranches
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {loan.tranches.map((t) => (
                        <span
                          key={t.id}
                          className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                            t.status === 'released'
                              ? 'bg-leaf-100 text-leaf-700'
                              : t.status === 'blocked'
                                ? 'bg-red-50 text-red-600'
                                : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {t.label} · {inr(t.amount)}
                          <span className="ml-1 normal-case opacity-70">{t.status}</span>
                        </span>
                      ))}
                    </div>
                  </div>

                  {loan.risk_events.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {loan.risk_events.map((r) => (
                        <span
                          key={r.id}
                          className={`badge ${
                            r.severity === 'severe'
                              ? 'bg-red-100 text-red-700'
                              : r.severity === 'moderate'
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-yellow-50 text-yellow-700'
                          }`}
                        >
                          {r.event_type} · {r.severity} [{r.loss_ratio} loss]
                          {r.action === 'pause' && ' · repayments paused'}
                          {r.action === 'block_tranches' && ' · tranches blocked'}
                          {r.action === 'moratorium' && ' · moratorium'}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 max-h-24 space-y-1 overflow-auto text-xs text-gray-500">
                    {loan.settlements.map((s, i) => (
                      <div key={s.id} className="flex items-center justify-between rounded bg-leaf-50/50 px-2 py-1">
                        <span>
                          Sale #{i + 1} · {s.crop || '—'} · {inr(s.sale_value)}
                        </span>
                        <span>
                          FPO fee {inr(s.fpo_facilitation_amt)} · EMI {inr(s.emi_paid)} · residual{' '}
                          {inr(s.residual_to_farmer)}
                        </span>
                      </div>
                    ))}
                  </div>

                  {active && (
                    <form
                      onSubmit={settleSale}
                      className="mt-4 flex flex-wrap items-end gap-3 border-t border-gray-100 pt-4"
                    >
                      <div>
                        <label className="field-label">Loan</label>
                        <select
                          className="input-base"
                          value={settle.loan_id}
                          onChange={(e) => setSettle({ ...settle, loan_id: e.target.value })}
                        >
                          {loans.map((l) => (
                            <option key={l.id} value={l.id}>
                              {l.application_uid} · {inr(l.principal)}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="field-label">Mandi sale value (₹)</label>
                        <input
                          type="number"
                          min="1"
                          className="input-base"
                          placeholder="e.g. 132000"
                          value={settle.sale_value}
                          onChange={(e) => setSettle({ ...settle, sale_value: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <label className="field-label">Crop</label>
                        <input
                          className="input-base"
                          value={settle.crop}
                          onChange={(e) => setSettle({ ...settle, crop: e.target.value })}
                        />
                      </div>
                      <button className="btn-primary py-2 disabled:opacity-50" disabled={loanBusy > 0}>
                        Settle escrow
                      </button>
                    </form>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}