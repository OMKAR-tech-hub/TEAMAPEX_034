import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const ROLES = [
  { key: 'farmer', label: 'Farmer', blurb: 'Land & crop identity', dot: 'bg-leaf-500' },
  { key: 'fpo', label: 'FPO', blurb: 'Farmer Producer Org', dot: 'bg-amber-500' },
  { key: 'bank', label: 'Bank', blurb: 'Lender institution', dot: 'bg-sky-500' },
]

const EMPTY_FARMER = {
  name: '',
  mobile: '',
  password: '',
  village: '',
  district: '',
  state: '',
  acreage: '',
  primary_crop: '',
  crop_season: 'Kharif 2025',
  fpo_membership: '',
}

const EMPTY_ORG = { name: '', username: '', password: '' }

export default function Register() {
  const [role, setRole] = useState('farmer')
  const [farmer, setFarmer] = useState(EMPTY_FARMER)
  const [org, setOrg] = useState(EMPTY_ORG)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { registerFarmer, registerOrg } = useAuth()
  const navigate = useNavigate()

  const setF = (key) => (e) => setFarmer({ ...farmer, [key]: e.target.value })
  const setO = (key) => (e) => setOrg({ ...org, [key]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (role === 'farmer') {
        await registerFarmer({
          ...farmer,
          acreage: parseFloat(farmer.acreage),
          fpo_membership: farmer.fpo_membership || null,
        })
      } else {
        await registerOrg(role, org)
      }
      navigate(`/${role}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="card p-8 sm:p-10">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create an account</h1>
          <p className="mt-1 text-sm text-gray-500">
            Choose your role to begin building your Kisan Setu ecosystem identity.
          </p>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3">
          {ROLES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => setRole(r.key)}
              className={`rounded-2xl border-2 p-4 text-left transition ${
                role === r.key
                  ? 'border-leaf-600 bg-leaf-50 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-leaf-300'
              }`}
            >
              <div className={`h-2.5 w-2.5 rounded-full ${r.dot} ${role === r.key ? '' : 'opacity-40'}`} />
              <div className="mt-2 text-sm font-semibold">{r.label}</div>
              <div className="mt-0.5 text-xs text-gray-500">{r.blurb}</div>
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {role === 'farmer' ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="field-label">Full Name *</label>
                  <input className="input-base" value={farmer.name} onChange={setF('name')} required />
                </div>
                <div>
                  <label className="field-label">Mobile Number *</label>
                  <input
                    className="input-base"
                    value={farmer.mobile}
                    onChange={setF('mobile')}
                    pattern="\d{10}"
                    maxLength={10}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Password *</label>
                  <input
                    type="password"
                    className="input-base"
                    value={farmer.password}
                    onChange={setF('password')}
                    minLength={6}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Village *</label>
                  <input className="input-base" value={farmer.village} onChange={setF('village')} required />
                </div>
                <div>
                  <label className="field-label">District *</label>
                  <input className="input-base" value={farmer.district} onChange={setF('district')} required />
                </div>
                <div>
                  <label className="field-label">State *</label>
                  <input className="input-base" value={farmer.state} onChange={setF('state')} required />
                </div>
                <div>
                  <label className="field-label">Acreage (acres) *</label>
                  <input
                    className="input-base"
                    value={farmer.acreage}
                    onChange={setF('acreage')}
                    type="number"
                    min="0.1"
                    step="0.1"
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Primary Crop *</label>
                  <input
                    className="input-base"
                    value={farmer.primary_crop}
                    onChange={setF('primary_crop')}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Crop Season</label>
                  <input className="input-base" value={farmer.crop_season} onChange={setF('crop_season')} />
                </div>
                <div>
                  <label className="field-label">FPO Membership</label>
                  <input className="input-base" value={farmer.fpo_membership} onChange={setF('fpo_membership')} />
                </div>
              </div>
            </>
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="field-label">Organization Name *</label>
                <input className="input-base" value={org.name} onChange={setO('name')} required />
              </div>
              <div>
                <label className="field-label">Username *</label>
                <input className="input-base" value={org.username} onChange={setO('username')} required />
              </div>
              <div>
                <label className="field-label">Password *</label>
                <input
                  type="password"
                  className="input-base"
                  value={org.password}
                  onChange={setO('password')}
                  minLength={6}
                  required
                />
              </div>
            </div>
          )}

          <button disabled={busy} className="btn-primary w-full py-2.5">
            {busy ? 'Creating account...' : `Register as ${ROLES.find((r) => r.key === role).label}`}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already registered?{' '}
          <Link className="font-semibold text-leaf-600 hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}