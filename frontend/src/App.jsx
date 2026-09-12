import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import FarmerDashboard from './pages/FarmerDashboard';
import TrustPassport from './pages/TrustPassport';
import WhatIf from './pages/WhatIf';
import ConsentManagement from './pages/ConsentManagement';
import CreditApplication from './pages/CreditApplication';
import FPODashboard from './pages/FPODashboard';
import LenderDashboard from './pages/LenderDashboard';
import DataAccessHistory from './pages/DataAccessHistory';

function RequireAuth({ children }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<FarmerDashboard />} />
          <Route path="passport" element={<TrustPassport />} />
          <Route path="what-if" element={<WhatIf />} />
          <Route path="consent" element={<ConsentManagement />} />
          <Route path="credit" element={<CreditApplication />} />
          <Route path="fpo" element={<FPODashboard />} />
          <Route path="lender" element={<LenderDashboard />} />
          <Route path="access-history" element={<DataAccessHistory />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
