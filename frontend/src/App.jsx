import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import Navbar from './components/Navbar.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import FarmerDashboard from './pages/FarmerDashboard.jsx'
import FPODashboard from './pages/FPODashboard.jsx'
import BankDashboard from './pages/BankDashboard.jsx'

function RequireRole({ role, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={`/${user.role}`} replace />
  return children
}

function Home() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={`/${user.role}`} replace />
}

export default function App() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/farmer"
          element={
            <RequireRole role="farmer">
              <FarmerDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/fpo"
          element={
            <RequireRole role="fpo">
              <FPODashboard />
            </RequireRole>
          }
        />
        <Route
          path="/bank"
          element={
            <RequireRole role="bank">
              <BankDashboard />
            </RequireRole>
          }
        />
        {user && <Route path="*" element={<Navigate to={`/${user.role}`} replace />} />}
      </Routes>
    </div>
  )
}