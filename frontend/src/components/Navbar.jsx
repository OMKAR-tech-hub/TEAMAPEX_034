import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const ROLE_LABELS = { farmer: 'Farmer', fpo: 'FPO', bank: 'Bank' }
const ROLE_STYLES = {
  farmer: 'bg-leaf-600',
  fpo: 'bg-amber-500',
  bank: 'bg-sky-600',
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-leaf-900/20 bg-leaf-800/95 text-white backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/15">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
              />
            </svg>
          </span>
          Kisan <span className="text-leaf-100">Setu</span>
        </Link>

        {user ? (
          <nav className="flex items-center gap-3 text-sm">
            <Link className="rounded-md px-2 py-1 hover:bg-white/10" to={`/${user.role}`}>
              Dashboard
            </Link>
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-leaf-50 ${ROLE_STYLES[user.role] || 'bg-leaf-700'}`}
            >
              <span className="font-medium">{user.name}</span>
              <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">
                {ROLE_LABELS[user.role] || user.role}
              </span>
            </span>
            <button
              className="rounded-lg border border-white/25 px-3 py-1 font-medium hover:bg-white/10"
              onClick={onLogout}
            >
              Logout
            </button>
          </nav>
        ) : (
          <nav className="flex items-center gap-3 text-sm">
            <Link className="rounded-md px-2 py-1 hover:bg-white/10" to="/login">
              Login
            </Link>
            <Link
              className="rounded-lg bg-leaf-500 px-3 py-1.5 font-medium hover:bg-leaf-400"
              to="/register"
            >
              Register
            </Link>
          </nav>
        )}
      </div>
    </header>
  )
}