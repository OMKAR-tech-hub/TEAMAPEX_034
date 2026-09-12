import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getMe } from '../api';

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const role = localStorage.getItem('role');

  useEffect(() => {
    getMe().then(r => setUser(r.data)).catch(() => {});
  }, []);

  function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  }

  const farmerLinks = [
    { to: '/dashboard',      label: '🌾 Dashboard' },
    { to: '/passport',       label: '📋 Trust Passport' },
    { to: '/what-if',        label: '🔮 What-If Simulator' },
    { to: '/consent',        label: '🔐 My Consent' },
    { to: '/access-history', label: '📜 Data Access History' },
    { to: '/credit',         label: '💰 Credit Application' },
  ];
  const fpoLinks = [
    { to: '/fpo',      label: '🤝 FPO Dashboard' },
    { to: '/dashboard',label: '🌾 Farmers' },
  ];
  const lenderLinks = [
    { to: '/lender',   label: '🏦 Lender Dashboard' },
  ];
  const adminLinks = [
    { to: '/dashboard',label: '⚙️ Overview' },
    { to: '/fpo',      label: '🤝 FPOs' },
    { to: '/lender',   label: '🏦 Lenders' },
  ];

  let links = farmerLinks;
  if (role === 'fpo_manager') links = fpoLinks;
  else if (role === 'lender')  links = lenderLinks;
  else if (role === 'admin')   links = adminLinks;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          KisanSetu
          <span>Farmer Trust Passport</span>
        </div>
        <nav className="sidebar-nav">
          {links.map(l => (
            <NavLink key={l.to} to={l.to}
              className={({ isActive }) => isActive ? 'active' : ''}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {user && <div style={{ marginBottom: 8 }}>{user.email}</div>}
          <button className="sidebar-logout" onClick={logout}>🚪 Logout</button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
