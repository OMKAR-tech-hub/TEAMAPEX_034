import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api.js'

export default function Login() {
  const [mobile, setMobile] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const res = await api.post('/auth/login', { mobile, password })
      localStorage.setItem('token', res.data.access_token)
      localStorage.setItem('farmer', JSON.stringify(res.data.farmer))
      navigate('/profile')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>Farmer Login</h1>
        <p className="subtitle">Sign in with your mobile number and password.</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="mobile">Mobile Number</label>
            <input
              id="mobile"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              inputMode="numeric"
              maxLength={10}
              pattern="\d{10}"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Signing in...' : 'Login'}
          </button>
        </form>
        <p className="hint" style={{ marginTop: 16 }}>
          No account yet? <Link to="/register">Register as a farmer</Link>
        </p>
      </div>
    </div>
  )
}