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

// Приватный роут для защиты страниц.
// Неавторизованный пользователь попадает на приветственную страницу,
// а уже оттуда переходит к форме входа.
const PrivateRoute = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? <>{children}</> : <Navigate to="/welcome" replace />;
};

// Приветственная страница доступна только неавторизованным —
// если пользователь уже залогинен, отправляем на главную.
const PublicOnlyRoute = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
};

// Роут для админа и аналитика ДРВЦ
const AdminRoute = ({ children }: { children: ReactNode }) => {
  const lsToken = localStorage.getItem('token');
  let hasAdminAccess = false;
  if (lsToken) {
      try {
          const decoded: { is_admin?: boolean; role?: string } = jwtDecode(lsToken);
          // Админ, директор или аналитик ДРВЦ имеют доступ к админке
          hasAdminAccess = decoded.is_admin === true || decoded.role === 'ANALYST_DRVC' || decoded.role === 'DIRECTOR_DRVC' || decoded.role === 'ANALYST_MANAGER';
      } catch { /* ignore */ }
  }

  return hasAdminAccess ? <>{children}</> : <Navigate to="/" />;
};

// Роут для главной страницы с редиректом аналитика ДРВЦ на страницу ПСД
const HomeRoute = ({ children }: { children: ReactNode }) => {
  const lsToken = localStorage.getItem('token');
  let isAnalyst = false;
  if (lsToken) {
      try {
          const decoded: { role?: string } = jwtDecode(lsToken);
          isAnalyst = decoded.role === 'ANALYST_DRVC' || decoded.role === 'DIRECTOR_DRVC' || decoded.role === 'ANALYST_MANAGER';
      } catch { /* ignore */ }
  }

  // Аналитик или директор ДРВЦ редиректится на /psd-analyst
  if (isAnalyst) {
      return <Navigate to="/psd-analyst" />;
  }

  return <>{children}</>;
};

function App() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem('token'));
    };
    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const handleSetToken = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/welcome" element={<PublicOnlyRoute><Welcome /></PublicOnlyRoute>} />
        <Route path="/login" element={<PublicOnlyRoute><Login setToken={handleSetToken} /></PublicOnlyRoute>} />

        {/* Защищенные маршруты */}
        <Route 
          path="/" 
          element={<PrivateRoute><HomeRoute><Dashboard /></HomeRoute></PrivateRoute>} 
        />
        <Route
          path="/admin"
          element={<PrivateRoute><AdminRoute><AdminPage /></AdminRoute></PrivateRoute>}
        />
        <Route 
          path="/plans/:planId" 
          element={<PrivateRoute><PlanForm /></PrivateRoute>} 
        />
        <Route 
          path="/plans/:planId/items/new" 
          element={<PrivateRoute><PlanItemForm /></PrivateRoute>} 
        />
        <Route 
          path="/items/:itemId/edit" 
          element={<PrivateRoute><PlanItemForm /></PrivateRoute>} 
        />

        <Route
          path="/psd-analyst"
          element={<PrivateRoute><AdminRoute><PsdAnalystPage /></AdminRoute></PrivateRoute>}
        />

        <Route
          path="/ktp-search"
          element={<PrivateRoute><AdminRoute><KtpSearchPage /></AdminRoute></PrivateRoute>}
        />

        <Route path="*" element={
          <Navigate to={localStorage.getItem('token') ? '/' : '/welcome'} replace />
        } />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
