import { useEffect, useState } from 'react'
import api from '../api.js'

export default function BankDashboard() {
  const [farmers, setFarmers] = useState([])
  const [view, setView] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [loans, setLoans] = useState([])
  const [loanBusy, setLoanBusy] = useState(0)

  const reloadLoans = () =>
    api
      .get('/loans')
      .then((res) => setLoans(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load loans'))

  useEffect(() => {
    api
      .get('/bank/farmers')
      .then((res) => setFarmers(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load consented farmers'))
    reloadLoans()
  }, [])

  const approveLoan = async (loan) => {
    setLoanBusy((n) => n + 1)
    try {
      await api.post(`/loans/${loan.id}/approve`)
      await reloadLoans()
    } catch (e) {
      setError(e.response?.data?.detail || 'Approval failed')
    } finally {
      setLoanBusy((n) => n - 1)
    }
  }

  const releaseTranche = async (loan, tranche) => {
    setLoanBusy((n) => n + 1)
    try {
      await api.post(`/loans/${loan.id}/release-tranche`, { tranche_id: tranche.id })
      await reloadLoans()
    } catch (e) {
      setError(e.response?.data?.detail || 'Tranche release failed')
    } finally {
      setLoanBusy((n) => n - 1)
    }
  }

  const exportPsl = async () => {
    setError('')
    try {
      const res = await api.get('/bank/export/psl', { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'psl_export.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.response?.data?.detail || 'Export failed')
    }
  }

  const openView = async (farmerId) => {
    setLoading(true)
    setView(null)
    setError('')
    try {
      const res = await api.get(`/bank/farmers/${farmerId}/view`)
      setView(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load farmer view')
    } finally {
      setLoading(false)
    }
  }

  const field = (label, value, masked = false) => (
    <div className="flex items-center justify-between border-b border-gray-100 py-2 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span
        className={`font-medium ${
          masked ? 'font-mono text-xs text-gray-400' : 'font-semibold text-gray-900'
        }`}
      >
        {value || '—'}
      </span>
    </div>
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
        <h1 className="text-2xl font-bold text-gray-900">Bank Origination Queue</h1>
        <p className="text-sm text-gray-500">
          Consent-gated farmer passports. Only granted attributes are visible.
        </p>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statCard('Consented Farmers', farmers.length)}
        {statCard(
          'Max Safe Credit',
          farmers.length
            ? `₹${Math.max(...farmers.map((f) => f.safe_credit_limit ?? 0)).toLocaleString('en-IN')}`
            : '—',
          'text-leaf-700',
        )}
        {statCard('Active Loans', loans.filter((l) => !['repaid', 'underwritten'].includes(l.status)).length, 'text-amber-600')}
        {statCard(
          'Disbursed',
          loans.length ? `₹${loans.reduce((s, l) => s + (l.amount_disbursed ?? 0), 0).toLocaleString('en-IN')}` : '—',
          'sum of tranches released',
          'text-sky-600',
        )}
      </div>

      <div className="card mt-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Loan Pipeline & Tranche Engine</h2>
            <p className="mt-1 text-sm text-gray-500">
              Approve underwritten loans, then release tranches as release rules pass. Risk events
              block pending tranches automatically.
            </p>
          </div>
          <button onClick={exportPsl} className="btn-ghost px-4 py-2">
            Export PSL report (CSV)
          </button>
        </div>

        {loans.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">
            No loans yet. Farmers raise loans after an approved underwrite.
          </p>
        ) : (
          <div className="mt-4 grid gap-4 text-sm lg:grid-cols-2">
            {loans.map((loan) => (
              <div key={loan.id} className="rounded-2xl border border-gray-200 p-5">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="font-medium text-gray-900">
                      {loan.farmer_name} · {loan.application_uid}
                    </div>
                    <div className="text-xs text-gray-500">
                      {loan.farmer_id} · {loan.psl_category}
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="badge bg-indigo-50 text-indigo-700 normal-case">
                        {loan.purpose_category?.replace(/_/g, ' ') || 'working capital'}
                      </span>
                      <span className="badge bg-amber-50 text-amber-700 normal-case">
                        risk {loan.agri_risk_tier || 'n/a'}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`badge ${
                      loan.status === 'repaid'
                        ? 'bg-leaf-100 text-leaf-700'
                        : ['active', 'disbursing', 'approved'].includes(loan.status)
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-sky-100 text-sky-700'
                    }`}
                  >
                    {loan.status}
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-gray-50 px-2 py-2">
                    <div className="text-xs text-gray-500">Principal</div>
                    <div className="font-bold">₹{Number(loan.principal).toLocaleString('en-IN')}</div>
                  </div>
                  <div className="rounded-lg bg-gray-50 px-2 py-2">
                    <div className="text-xs text-gray-500">Disbursed</div>
                    <div className="font-bold text-leaf-700">₹{Number(loan.amount_disbursed).toLocaleString('en-IN')}</div>
                  </div>
                  <div className="rounded-lg bg-gray-50 px-2 py-2">
                    <div className="text-xs text-gray-500">Outstanding</div>
                    <div className="font-bold text-amber-600">₹{Number(loan.outstanding).toLocaleString('en-IN')}</div>
                  </div>
                </div>

                <div className="mt-3 space-y-1.5">
                  {loan.tranches.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{t.label}</span>
                        <span className="text-xs text-gray-400">→ {t.payee_ref}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">₹{Number(t.amount).toLocaleString('en-IN')}</span>
                        {t.status === 'scheduled' && (
                          <button
                            onClick={() => releaseTranche(loan, t)}
                            disabled={loanBusy > 0}
                            className="rounded-lg bg-leaf-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-leaf-700 disabled:opacity-50"
                          >
                            Release
                          </button>
                        )}
                        {t.status === 'released' && (
                          <span className="text-xs font-medium text-leaf-700">released</span>
                        )}
                        {t.status === 'blocked' && (
                          <span className="text-xs font-medium text-red-600">blocked by risk event</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {loan.status === 'underwritten' && (
                  <button
                    onClick={() => approveLoan(loan)}
                    disabled={loanBusy > 0}
                    className="btn-primary mt-4 w-full py-2 disabled:opacity-50"
                  >
                    Approve & generate tranches
                  </button>
                )}
                {loan.risk_events.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {loan.risk_events.map((r) => (
                      <span key={r.id} className="badge bg-red-50 text-red-600 normal-case">
                        {r.event_type} ({r.severity}) — {r.action}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="card h-fit p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Pipeline</h2>
            <span className="badge bg-leaf-100 text-leaf-700">{farmers.length} ready</span>
          </div>
          {farmers.length === 0 ? (
            <p className="mt-4 text-sm text-gray-500">
              No consented farmers yet. Ask a farmer to grant consent first.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {farmers.map((f) => (
                <li key={f.consent_id}>
                  <button
                    onClick={() => openView(f.farmer_id)}
                    className={`w-full rounded-xl border p-4 text-left transition ${
                      view?.farmer_id === f.farmer_id
                        ? 'border-leaf-500 bg-leaf-50 shadow-sm'
                        : 'border-gray-200 bg-white hover:border-leaf-300 hover:bg-leaf-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{f.farmer_name}</div>
                      {f.credit_tier && (
                        <span className="badge bg-amber-100 text-amber-700">{f.credit_tier}</span>
                      )}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {f.village} · {f.farmer_id}
                    </div>
                    {f.safe_credit_limit != null && (
                      <div className="mt-2 text-sm font-bold text-leaf-700">
                        ₹{Number(f.safe_credit_limit).toLocaleString('en-IN')}
                        <span className="ml-1 text-[10px] font-medium normal-case text-gray-400">
                          safe credit
                        </span>
                      </div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="lg:col-span-2">
          {loading && (
            <div className="card flex items-center gap-3 p-8 text-sm text-gray-500">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-leaf-500 border-t-transparent" />
              Loading farmer view...
            </div>
          )}

          {!loading && !view && !error && (
            <div className="card p-10 text-center text-sm text-gray-500">
              Select a farmer to see their consent-gated profile and Trust Passport breakdown.
            </div>
          )}

          {!loading && view && (
            <div className="card p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    Farmer View — {view.farmer_id}
                  </h2>
                  <div className="text-xs text-gray-500">
                    Visible to {view.bank_name} under consent #{view.consent_id}
                  </div>
                </div>
                {view.safe_credit_limit !== null ? (
                  <div className="text-right">
                    <div className="text-2xl font-bold text-leaf-700">
                      ₹{Number(view.safe_credit_limit).toLocaleString('en-IN')}
                    </div>
                    <div className="text-xs text-gray-500">
                      Safe Credit Limit · {view.credit_tier}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">Pass score not included in consent</div>
                )}
              </div>

              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <div>
                  <h3 className="text-sm font-semibold text-gray-600">Visible attributes</h3>
                  <div className="mt-2 rounded-xl border border-gray-100 px-4 py-1">
                    {view.fields.map((f) => (
                      <div key={f.attribute}>{field(f.attribute, f.value, f.masked)}</div>
                    ))}
                  </div>
                </div>

                {view.component_scores && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-600">Score breakdown</h3>
                    <div className="mt-2 grid gap-3 sm:grid-cols-2">
                      {Object.entries(view.component_scores).map(([key, val]) => (
                        <div
                          key={key}
                          className="flex justify-between rounded-xl border border-gray-100 bg-white/70 px-4 py-2.5 text-sm"
                        >
                          <span className="capitalize text-gray-600">{key}</span>
                          <span className="font-bold">{val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-between rounded-xl border border-dashed border-leaf-200 bg-leaf-50 px-4 py-3 text-sm">
                <span className="text-leaf-800">
                  Consent #{view.consent_id} is active. Masked fields are shown as <code>xxxxxx</code>.
                </span>
                <span className="badge bg-leaf-600 text-white">DLG compliant</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}