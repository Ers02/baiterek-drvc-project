// src/pages/Login.tsx
import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material'
import { Login as LoginIcon } from '@mui/icons-material'
import api from '../services/api'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [iin, setIin] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async () => {
    if (!iin || !password) {
      setError('Заполните все поля')
      return
    }

    try {
      setLoading(true)
      setError('')
      const res = await api.post('/auth/login', { iin, password })
      localStorage.setItem('token', res.data.token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.message || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      bgcolor="#f5f5f5"
    >
      <Paper elevation={10} sx={{ p: 6, width: 420, borderRadius: 3 }}>
        <Box textAlign="center" mb={4}>
          <LoginIcon sx={{ fontSize: 60, color: 'primary.main' }} />
          <Typography variant="h5" fontWeight="bold" mt={2}>
            Вход в систему
          </Typography>
          <Typography color="text.secondary">
            Портал заявок на закупки
          </Typography>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <TextField
          label="ИИН"
          fullWidth
          margin="normal"
          value={iin}
          onChange={(e) => setIin(e.target.value)}
          disabled={loading}
          inputProps={{ maxLength: 12 }}
        />

        <TextField
          label="Пароль"
          type="password"
          fullWidth
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
        />

        <Button
          variant="contained"
          size="large"
          fullWidth
          sx={{ mt: 4, py: 1.5 }}
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} /> : 'Войти'}
        </Button>

        <Typography textAlign="center" color="text.secondary" mt={3}>
          © 2025 Портал закупок
        </Typography>
      </Paper>
    </Box>
  )
}