// src/pages/Login.tsx
import {useState, type FormEvent} from 'react'
import {
    Box,
    Paper,
    Typography,
    TextField,
    Button,
    CircularProgress,
    Alert,
    InputAdornment,
    IconButton,
} from '@mui/material'
import {
    Login as LoginIcon,
    Person as PersonIcon,
    Lock as LockIcon,
    Visibility as VisibilityIcon,
    VisibilityOff as VisibilityOffIcon,
    ArrowBack as ArrowBackIcon,
} from '@mui/icons-material'
import api from '../services/api'
import {useNavigate} from 'react-router-dom'
import {jwtDecode} from 'jwt-decode'
import {UserRole} from '../services/api.types'

interface LoginProps {
    setToken: (token: string) => void;
}

export default function Login({setToken}: LoginProps) {
    const [iin, setIin] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()

    const handleLogin = async (e?: FormEvent) => {
        if (e) e.preventDefault();

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
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            });

            const token = res.data.access_token;
            localStorage.setItem('token', token);
            setToken(token);

            try {
                const decoded: { role?: string; is_admin?: boolean } = jwtDecode(token);
                const role = decoded.role as UserRole;

                if (role === UserRole.ANALYST_DRVC || role === UserRole.DIRECTOR_DRVC || role === UserRole.ANALYST_MANAGER) {
                    navigate('/psd-analyst');
                } else if (decoded.is_admin === true || role === UserRole.ADMIN) {
                    navigate('/admin');
                } else {
                    navigate('/');
                }
            } catch {
                navigate('/');
            }
        } catch (err: unknown) {
            const errorDetail = err instanceof Error ? (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail : undefined;
            if (Array.isArray(errorDetail)) {
                const firstError = errorDetail[0] as { msg?: string } | undefined;
                setError(firstError?.msg || 'Ошибка валидации данных');
            } else {
                setError(typeof errorDetail === 'string' ? errorDetail : 'Неверный ИИН или пароль');
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <Box sx={{
            minHeight: '100vh',
            position: 'relative',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'hidden',
            background: 'linear-gradient(135deg, #062f1d 0%, #0b4b32 50%, #116745 100%)',
        }}>
            {/* Декоративные размытые круги фона */}
            <Box sx={{
                position: 'absolute',
                top: '-15%', left: '-10%',
                width: 500, height: 500,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%)',
                filter: 'blur(40px)',
                animation: 'float 8s ease-in-out infinite',
                '@keyframes float': {
                    '0%, 100%': {transform: 'translate(0, 0)'},
                    '50%': {transform: 'translate(40px, 40px)'},
                },
            }}/>
            <Box sx={{
                position: 'absolute',
                bottom: '-15%', right: '-10%',
                width: 600, height: 600,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(76,175,80,0.25) 0%, transparent 70%)',
                filter: 'blur(50px)',
                animation: 'float2 10s ease-in-out infinite',
                '@keyframes float2': {
                    '0%, 100%': {transform: 'translate(0, 0)'},
                    '50%': {transform: 'translate(-50px, -30px)'},
                },
            }}/>

            {/* Кнопка "Назад" */}
            <Button
                startIcon={<ArrowBackIcon/>}
                onClick={() => navigate('/welcome')}
                sx={{
                    position: 'absolute',
                    top: 24, left: 24,
                    color: 'rgba(255,255,255,0.85)',
                    textTransform: 'none',
                    fontWeight: 500,
                    zIndex: 2,
                    '&:hover': {
                        color: 'white',
                        bgcolor: 'rgba(255,255,255,0.08)',
                    },
                }}
            >
                Назад
            </Button>

            {/* Карточка формы */}
            <Paper
                elevation={0}
                sx={{
                    position: 'relative', zIndex: 1,
                    width: {xs: '90%', sm: 440},
                    p: {xs: 4, sm: 5},
                    borderRadius: 4,
                    background: 'rgba(255,255,255,0.97)',
                    backdropFilter: 'blur(20px)',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                    animation: 'fadeInUp 0.6s ease-out',
                    '@keyframes fadeInUp': {
                        '0%': {opacity: 0, transform: 'translateY(30px)'},
                        '100%': {opacity: 1, transform: 'translateY(0)'},
                    },
                }}
            >
                <form onSubmit={handleLogin}>
                    {/* Логотип + заголовок */}
                    <Box textAlign="center" mb={4}>
                        <Box
                            component="img"
                            src="/baiterek.png"
                            alt="Байтерек"
                            sx={{
                                width: 64, height: 'auto', mb: 2,
                                filter: 'drop-shadow(0 4px 12px rgba(11,75,50,0.25))',
                            }}
                            onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                                (e.currentTarget as HTMLImageElement).src = '/baiterek.svg';
                            }}
                        />
                        <Typography sx={{
                            color: '#0b4b32',
                            letterSpacing: 3,
                            fontWeight: 600,
                            fontSize: '0.7rem',
                            textTransform: 'uppercase',
                            mb: 0.5,
                        }}>
                            ДРВЦ Байтерек
                        </Typography>
                        <Typography variant="h4" fontWeight="bold" sx={{color: '#062f1d', mb: 0.5}}>
                            Вход в систему
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Войдите по ИИН и паролю
                        </Typography>
                    </Box>

                    {error && (
                        <Alert severity="error" sx={{mb: 2.5, borderRadius: 2}}>
                            {error}
                        </Alert>
                    )}

                    <TextField
                        label="ИИН"
                        fullWidth
                        margin="dense"
                        value={iin}
                        onChange={(e) => setIin(e.target.value)}
                        disabled={loading}
                        inputProps={{maxLength: 12, inputMode: 'numeric'}}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <PersonIcon sx={{color: '#116745'}}/>
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            mb: 1.5,
                            '& .MuiOutlinedInput-root': {
                                borderRadius: 2,
                                '&.Mui-focused fieldset': {borderColor: '#116745'},
                            },
                            '& label.Mui-focused': {color: '#116745'},
                        }}
                    />

                    <TextField
                        label="Пароль"
                        type={showPassword ? 'text' : 'password'}
                        fullWidth
                        margin="dense"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <LockIcon sx={{color: '#116745'}}/>
                                </InputAdornment>
                            ),
                            endAdornment: (
                                <InputAdornment position="end">
                                    <IconButton
                                        size="small"
                                        onClick={() => setShowPassword(s => !s)}
                                        edge="end"
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <VisibilityOffIcon/> : <VisibilityIcon/>}
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                borderRadius: 2,
                                '&.Mui-focused fieldset': {borderColor: '#116745'},
                            },
                            '& label.Mui-focused': {color: '#116745'},
                        }}
                    />

                    <Button
                        type="submit"
                        variant="contained"
                        size="large"
                        fullWidth
                        disabled={loading}
                        startIcon={!loading && <LoginIcon/>}
                        sx={{
                            mt: 3.5,
                            py: 1.5,
                            borderRadius: 50,
                            textTransform: 'none',
                            fontWeight: 'bold',
                            fontSize: '1rem',
                            background: 'linear-gradient(135deg, #0b4b32 0%, #116745 100%)',
                            boxShadow: '0 8px 20px rgba(11,75,50,0.35)',
                            transition: 'all 0.3s',
                            '&:hover': {
                                background: 'linear-gradient(135deg, #0a3f2a 0%, #0e573a 100%)',
                                transform: 'translateY(-2px)',
                                boxShadow: '0 12px 26px rgba(11,75,50,0.45)',
                            },
                            '&.Mui-disabled': {
                                background: 'linear-gradient(135deg, #0b4b32 0%, #116745 100%)',
                                opacity: 0.7,
                                color: 'white',
                            },
                        }}
                    >
                        {loading ? <CircularProgress size={24} sx={{color: 'white'}}/> : 'Войти'}
                    </Button>

                    <Typography textAlign="center" color="text.secondary" mt={3} sx={{fontSize: '0.75rem'}}>
                        © 2026 · Департамент развития внутристрановой ценности
                    </Typography>
                </form>
            </Paper>
        </Box>
    )
}
