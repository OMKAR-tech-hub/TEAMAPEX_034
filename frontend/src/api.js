import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  // Keep the token that was used for this request. A dashboard request may
  // complete after the user has logged out (or logged in as someone else).
  // Its 401 must not clear the newer session.
  config.authToken = token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      // Only auto-logout if this is NOT an auth endpoint (login/register).
      // This prevents the interceptor from interfering with login form submissions
      // that return 401 on wrong credentials.
      const url = err.config?.url || ''
      const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register')
      const requestToken = err.config?.authToken
      const isCurrentSession = requestToken && requestToken === localStorage.getItem('token')
      if (!isAuthEndpoint && isCurrentSession) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        // Dispatch a custom event so AuthContext can react via React Router
        // (avoids a hard page reload that would break in-flight state).
        window.dispatchEvent(new Event('auth:logout'))
      }
    }
    return Promise.reject(err)
  }
)

export default api
