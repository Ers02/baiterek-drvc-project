import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import Login from './pages/Login';
import Welcome from './pages/Welcome';
import Dashboard from './pages/Dashboard';
import PlanForm from './pages/PlanForm';
import PlanItemForm from './pages/PlanItemForm';
import AdminPage from './pages/AdminPage';
import PsdAnalystPage from './pages/PsdAnalystPage';
import KtpSearchPage from './pages/KtpSearchPage';
import AppLayout from './components/AppLayout';

const PrivateRoute = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? <>{children}</> : <Navigate to="/welcome" replace />;
};

const PublicOnlyRoute = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
};

const AdminRoute = ({ children }: { children: ReactNode }) => {
  const lsToken = localStorage.getItem('token');
  let hasAdminAccess = false;
  if (lsToken) {
    try {
      const decoded: { is_admin?: boolean; role?: string } = jwtDecode(lsToken);
      hasAdminAccess =
        decoded.is_admin === true ||
        decoded.role === 'ANALYST_DRVC' ||
        decoded.role === 'DIRECTOR_DRVC' ||
        decoded.role === 'ANALYST_MANAGER';
    } catch { /* ignore */ }
  }
  return hasAdminAccess ? <>{children}</> : <Navigate to="/" />;
};

const HomeRoute = ({ children }: { children: ReactNode }) => {
  const lsToken = localStorage.getItem('token');
  let redirectToAnalyst = false;
  if (lsToken) {
    try {
      const decoded: { is_admin?: boolean; role?: string } = jwtDecode(lsToken);
      redirectToAnalyst =
        decoded.is_admin === true ||
        decoded.role === 'ANALYST_DRVC' ||
        decoded.role === 'DIRECTOR_DRVC' ||
        decoded.role === 'ANALYST_MANAGER';
    } catch { /* ignore */ }
  }
  if (redirectToAnalyst) return <Navigate to="/psd-analyst" />;
  return <>{children}</>;
};

function App() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    const handleStorageChange = () => setToken(localStorage.getItem('token'));
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const handleSetToken = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  return (
    <BrowserRouter>
      <Routes>
        {/* Публичные маршруты — без layout */}
        <Route path="/welcome" element={<PublicOnlyRoute><Welcome /></PublicOnlyRoute>} />
        <Route path="/login" element={<PublicOnlyRoute><Login setToken={handleSetToken} /></PublicOnlyRoute>} />

        {/* Защищённые маршруты с sidebar-лэйаутом */}
        <Route path="/" element={<PrivateRoute><AppLayout /></PrivateRoute>}>
          <Route index element={<HomeRoute><Dashboard /></HomeRoute>} />
          <Route path="admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
          <Route path="plans/:planId" element={<PlanForm />} />
          <Route path="plans/:planId/items/new" element={<PlanItemForm />} />
          <Route path="items/:itemId/edit" element={<PlanItemForm />} />
          <Route path="psd-analyst" element={<AdminRoute><PsdAnalystPage /></AdminRoute>} />
          <Route path="ktp-search" element={<AdminRoute><KtpSearchPage /></AdminRoute>} />
        </Route>

        <Route path="*" element={
          <Navigate to={localStorage.getItem('token') ? '/' : '/welcome'} replace />
        } />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
