import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api.js'

export default function Profile() {
  const [farmer, setFarmer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
      return
    }
    api
      .get('/auth/me')
      .then((res) => {
        setFarmer(res.data)
        localStorage.setItem('farmer', JSON.stringify(res.data))
      })
      .catch(() => setError('Could not load your profile.'))
      .finally(() => setLoading(false))
  }, [navigate])

  if (loading) {
    return (
      <div className="container">
        <p className="hint">Loading profile...</p>
      </div>
    )
  }

  if (!farmer) {
    return (
      <div className="container">
        <div className="card">
          <div className="error">{error || 'Not authenticated.'}</div>
          <Link to="/login">Go to login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <h1>Farmer Passport</h1>
        <p className="subtitle">Your verified agricultural identity.</p>

        {farmer.profile_photo && (
          <img
            className="profile-photo"
            src={farmer.profile_photo}
            alt="Profile"
            onError={(e) => (e.target.style.display = 'none')}
          />
        )}

        <dl>
          <div>
            <dt>Farmer ID</dt>
            <dd>{farmer.farmer_id}</dd>
          </div>
          <div>
            <dt>Name</dt>
            <dd>{farmer.name}</dd>
          </div>
          <div>
            <dt>Mobile</dt>
            <dd>{farmer.mobile}</dd>
          </div>
          <div>
            <dt>Village</dt>
            <dd>{farmer.village}</dd>
          </div>
          <div>
            <dt>District</dt>
            <dd>{farmer.district}</dd>
          </div>
          <div>
            <dt>State</dt>
            <dd>{farmer.state}</dd>
          </div>
          <div>
            <dt>FPO Membership</dt>
            <dd>{farmer.fpo_membership || '—'}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}