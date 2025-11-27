import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import {ApplicationForm} from './pages/ApplicationForm'
import { useState } from 'react'

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')

  const isAuthenticated = !!token

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login setToken={setToken} />} />
        <Route
          path="/"
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/application/new"
          element={isAuthenticated ? <ApplicationForm /> : <Navigate to="/login" />}
        />
        <Route
          path="/application/:id"
          element={isAuthenticated ? <ApplicationForm /> : <Navigate to="/login" />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App