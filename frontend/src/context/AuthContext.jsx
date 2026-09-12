import { createContext, useContext, useState } from 'react'
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
    const { data } = await api.post('/auth/register/farmer', payload)
    await login(payload.mobile, payload.password)
    return data
  }

  const registerOrg = async (role, payload) => {
    const { data } = await api.post(`/auth/register/${role}`, payload)
    await login(payload.username, payload.password)
    return data
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
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