// src/pages/Login.tsx
import { useState, FormEvent } from 'react'
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
import { jwtDecode } from 'jwt-decode'

interface LoginProps {
  setToken: (token: string) => void;
}

export default function Login({ setToken }: LoginProps) {
  const [iin, setIin] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e?: FormEvent) => {
    // Предотвращаем перезагрузку страницы
    if (e) {
      e.preventDefault();
    }

    if (!iin || !password) {
      setError('Заполните все поля')
      return
    }

    try {
      setLoading(true)
      setError('')
      
      const params = new URLSearchParams();
      params.append('username', iin);
      params.append('password', password);

      const res = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const token = res.data.access_token;
      localStorage.setItem('token', token);
      setToken(token);
      
      // Редирект в зависимости от роли
      try {
        const decoded: any = jwtDecode(token);
        if (decoded.role === 'analyst_drvc') {
          navigate('/psd-analyst');
        } else if (decoded.is_admin === true) {
          navigate('/admin');
        } else {
          navigate('/');
        }
      } catch (e) {
        navigate('/');
      }
    } catch (err: any) {
      // Важно: берем ошибку из ответа бэкенда
      const errorDetail = err.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
          setError(errorDetail[0]?.msg || 'Ошибка валидации данных');
      } else {
          setError(errorDetail || 'Неверный ИИН или пароль');
      }
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
        <form onSubmit={handleLogin}>
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
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            sx={{ mt: 4, py: 1.5 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Войти'}
          </Button>

          <Typography textAlign="center" color="text.secondary" mt={3}>
            © 2025 Портал закупок
          </Typography>
        </form>
      </Paper>
    </Box>
  )
}
