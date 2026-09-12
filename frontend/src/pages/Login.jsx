import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const FEATURES = [
  'Farmer-owned Trust Passport',
  'Consent-gated data sharing',
  'Deterministic & fair credit scoring',
  'Zero fees on farmers (RBI DLG)',
]

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const doLogin = async (u, p) => {
    setError('')
    setBusy(true)
    try {
      const data = await login(u, p)
      navigate(`/${data.role}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    doLogin(username, password)
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-6xl items-center px-4 py-10">
      <div className="grid w-full overflow-hidden rounded-3xl border border-gray-200/80 bg-white shadow-xl lg:grid-cols-2">
        {/* Hero panel */}
        <div className="relative hidden bg-gradient-to-br from-leaf-800 via-leaf-600 to-emerald-500 p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="text-2xl font-bold tracking-tight">
              Kisan <span className="text-leaf-100">Setu</span>
            </div>
            <h1 className="mt-8 text-3xl font-bold leading-tight">
              Your farm, your data,
              <br />
              fair credit.
            </h1>
            <p className="mt-3 max-w-sm text-sm text-white/85">
              One consent-gated trust passport connecting smallholder farmers to banks and FPOs —
              with transparent, deliverable credit outcomes.
            </p>
            <ul className="mt-8 space-y-3 text-sm text-white/90">
              {FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-3">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20">
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-10 rounded-2xl bg-white/10 p-4 text-xs leading-relaxed text-white/80 backdrop-blur">
            Compliance base: RBI Digital Lending Guidelines. No charges are ever levied on the
            farmer borrower beyond contractual interest. Data shared only with explicit,
            revocable consent.
          </div>
        </div>

        {/* Form panel */}
        <div className="p-8 sm:p-12">
          <div className="lg:hidden">
            <div className="text-2xl font-bold tracking-tight text-leaf-700">
              Kisan <span className="text-leaf-500">Setu</span>
            </div>
          </div>

          <h2 className="mt-6 text-2xl font-bold text-gray-900">Sign in</h2>
          <p className="mt-1 text-sm text-gray-500">
            Farmers use their mobile number; FPOs and banks use their username.
          </p>

          {error && (
            <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-sm text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="field-label" htmlFor="username">
                Username / Mobile
              </label>
              <input
                id="username"
                className="input-base"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="input-base"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button disabled={busy} className="btn-primary w-full py-2.5">
              {busy ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              One-click demo logins
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                onClick={() => doLogin('fpo_krishak', 'demo@1234')}
                disabled={busy}
                className="btn-ghost"
              >
                FPO Krushak
              </button>
              <button
                onClick={() => doLogin('bank_gramin', 'demo@1234')}
                disabled={busy}
                className="btn-ghost"
              >
                Bank Gramin
              </button>
            </div>
            <p className="mt-3 text-xs text-gray-500">
              New farmer? Register with your mobile to get a Trust Passport.
            </p>
          </div>

          <p className="mt-6 text-center text-sm text-gray-500">
            No account yet?{' '}
            <Link className="font-semibold text-leaf-600 hover:underline" to="/register">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}