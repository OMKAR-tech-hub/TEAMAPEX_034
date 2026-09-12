import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import Register from './pages/Register.jsx'
import Login from './pages/Login.jsx'
import Profile from './pages/Profile.jsx'

function Nav() {
  const navigate = useNavigate()
  const farmer = JSON.parse(localStorage.getItem('farmer') || 'null')

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('farmer')
    navigate('/login')
  }

  return (
    <nav className="nav">
      <NavLink to="/" className="brand">
        Kisansetu
      </NavLink>
      <div>
        {farmer ? (
          <>
            <NavLink to="/profile">Profile</NavLink>
            <a href="#" onClick={logout}>
              Logout
            </a>
          </>
        ) : (
          <>
            <NavLink to="/register">Register</NavLink>
            <NavLink to="/login">Login</NavLink>
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </>
  )
}