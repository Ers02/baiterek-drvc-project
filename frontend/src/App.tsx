import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PlanForm from './pages/PlanForm';
import PlanItemForm from './pages/PlanItemForm';
import AdminPage from './pages/AdminPage';
import PsdAnalystPage from './pages/PsdAnalystPage';

// Приватный роут для защиты страниц
const PrivateRoute = ({ children }: { children: JSX.Element }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Роут для админа и аналитика ДРВЦ
const AdminRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  let hasAdminAccess = false;
  if (token) {
      try {
          const decoded: any = jwtDecode(token);
          // Админ или аналитик ДРВЦ имеют доступ к админке
          hasAdminAccess = decoded.is_admin === true || decoded.role === 'analyst_drvc';
      } catch (e) {}
  }

  return hasAdminAccess ? children : <Navigate to="/" />;
};

// Роут для главной страницы с редиректом аналитика ДРВЦ на страницу ПСД
const HomeRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  let isAnalyst = false;
  if (token) {
      try {
          const decoded: any = jwtDecode(token);
          isAnalyst = decoded.role === 'analyst_drvc';
      } catch (e) {}
  }

  // Аналитик ДРВЦ редиректится на /psd-analyst
  if (isAnalyst) {
      return <Navigate to="/psd-analyst" />;
  }

  return children;
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

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
        <Route path="/login" element={<Login setToken={handleSetToken} />} />
        
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
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
