import { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null)
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user') || 'null')
    } catch {
      return null
    }
  })
  const navigate = useNavigate()

  // Listen for forced-logout events emitted by api.js when any
  // non-auth request returns 401 (expired / invalid token).
  // Using a DOM event keeps api.js free of React dependencies and
  // avoids hard window.location.href reloads that break re-login.
  useEffect(() => {
    const handleForceLogout = () => {
      setToken(null)
      setUser(null)
      navigate('/login', { replace: true })
    }
    window.addEventListener('auth:logout', handleForceLogout)
    return () => window.removeEventListener('auth:logout', handleForceLogout)
  }, [navigate])

  const applySession = (data) => {
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }

  const login = async (username, password) => {
    const { data } = await api.post('/auth/login', { username, password })
    applySession(data)
    return data
  }

  const registerFarmer = async (payload) => {
    await api.post('/auth/register/farmer', payload)
    return login(payload.mobile, payload.password)
  }

  const registerOrg = async (role, payload) => {
    await api.post(`/auth/register/${role}`, payload)
    return login(payload.username, payload.password)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
    navigate('/login', { replace: true })
  }

  return (
    <AuthContext.Provider
      value={{ token, user, login, registerFarmer, registerOrg, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)