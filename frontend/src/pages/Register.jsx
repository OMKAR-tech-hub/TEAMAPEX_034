import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api.js'

const EMPTY = {
  name: '',
  mobile: '',
  password: '',
  farmer_id: '',
  village: '',
  district: '',
  state: '',
  fpo_membership: '',
}

export default function Register() {
  const [form, setForm] = useState(EMPTY)
  const [photo, setPhoto] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const payload = { ...form, farmer_id: form.farmer_id || undefined }
      const res = await api.post('/farmers', payload)

      if (photo) {
        const fd = new FormData()
        fd.append('photo', photo)
        await api.post(`/farmers/${res.data.farmer_id}/photo`, fd)
      }

      const loginRes = await api.post('/auth/login', {
        mobile: form.mobile,
        password: form.password,
      })
      localStorage.setItem('token', loginRes.data.access_token)
      localStorage.setItem('farmer', JSON.stringify(loginRes.data.farmer))
      navigate('/profile')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>Create a farmer account</h1>
        <p className="subtitle">Build your agricultural identity with Kisansetu.</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Full Name *</label>
            <input id="name" value={form.name} onChange={set('name')} required />
          </div>

          <div className="row">
            <div className="field">
              <label htmlFor="mobile">Mobile Number *</label>
              <input
                id="mobile"
                value={form.mobile}
                onChange={set('mobile')}
                inputMode="numeric"
                maxLength={10}
                pattern="\d{10}"
                title="10-digit mobile number"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password *</label>
              <input
                id="password"
                type="password"
                value={form.password}
                onChange={set('password')}
                minLength={6}
                required
              />
            </div>
          </div>

          <div className="row">
            <div className="field">
              <label htmlFor="village">Village *</label>
              <input id="village" value={form.village} onChange={set('village')} required />
            </div>
            <div className="field">
              <label htmlFor="district">District *</label>
              <input id="district" value={form.district} onChange={set('district')} required />
            </div>
          </div>

          <div className="row">
            <div className="field">
              <label htmlFor="state">State *</label>
              <input id="state" value={form.state} onChange={set('state')} required />
            </div>
            <div className="field">
              <label htmlFor="farmer_id">Farmer ID</label>
              <input
                id="farmer_id"
                value={form.farmer_id}
                onChange={set('farmer_id')}
                placeholder="Auto-generated"
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="fpo">FPO Membership</label>
            <input
              id="fpo"
              value={form.fpo_membership}
              onChange={set('fpo_membership')}
              placeholder="Optional"
            />
          </div>

          <div className="field">
            <label htmlFor="photo">Profile Photo</label>
            <input
              id="photo"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setPhoto(e.target.files[0])}
            />
            <div className="hint">Optional. JPG, PNG or WEBP.</div>
          </div>

          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Creating account...' : 'Register'}
          </button>
        </form>
      </div>
    </div>
  )
}