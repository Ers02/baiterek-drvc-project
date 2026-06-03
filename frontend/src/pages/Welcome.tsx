import {Box, Button, Container, Typography} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import {Login as LoginIcon} from '@mui/icons-material';

export default function Welcome() {
    const navigate = useNavigate();

    return (
        <Box sx={{
            minHeight: '100vh',
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
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
                background: 'radial-gradient(circle, rgba(100,181,246,0.25) 0%, transparent 70%)',
                filter: 'blur(50px)',
                animation: 'float2 10s ease-in-out infinite',
                '@keyframes float2': {
                    '0%, 100%': {transform: 'translate(0, 0)'},
                    '50%': {transform: 'translate(-50px, -30px)'},
                },
            }}/>

            <Container maxWidth="sm" sx={{position: 'relative', zIndex: 1, textAlign: 'center', px: 3}}>
                {/* Логотип */}
                <Box
                    component="img"
                    src="/baiterek.png"
                    alt="Байтерек"
                    sx={{
                        width: 140, height: 'auto',
                        mb: 4,
                        filter: 'drop-shadow(0 10px 30px rgba(0,0,0,0.3))',
                        animation: 'fadeInDown 0.8s ease-out',
                        '@keyframes fadeInDown': {
                            '0%': {opacity: 0, transform: 'translateY(-20px)'},
                            '100%': {opacity: 1, transform: 'translateY(0)'},
                        },
                    }}
                    onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                        (e.currentTarget as HTMLImageElement).src = '/baiterek.svg';
                    }}
                />

                {/* Заголовок */}
                <Typography sx={{
                    color: 'rgba(255,255,255,0.85)',
                    letterSpacing: 4,
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    mb: 2,
                    textTransform: 'uppercase',
                    animation: 'fadeIn 1s ease-out 0.2s both',
                    '@keyframes fadeIn': {
                        '0%': {opacity: 0},
                        '100%': {opacity: 1},
                    },
                }}>
                    Департамент Развития Внутристрановой Ценности
                </Typography>
                <Typography variant="h2" sx={{
                    color: 'white',
                    fontWeight: 800,
                    fontSize: {xs: '2.25rem', md: '3.5rem'},
                    lineHeight: 1.1,
                    mb: 3,
                    textShadow: '0 4px 20px rgba(0,0,0,0.2)',
                    animation: 'fadeInUp 0.8s ease-out 0.3s both',
                    '@keyframes fadeInUp': {
                        '0%': {opacity: 0, transform: 'translateY(20px)'},
                        '100%': {opacity: 1, transform: 'translateY(0)'},
                    },
                }}>
                    Добро пожаловать
                </Typography>
                <Typography sx={{
                    color: 'rgba(255,255,255,0.85)',
                    fontSize: {xs: '1rem', md: '1.15rem'},
                    fontWeight: 300,
                    mb: 5,
                    maxWidth: 450, mx: 'auto', lineHeight: 1.6,
                    animation: 'fadeInUp 0.8s ease-out 0.5s both',
                }}>
                    Портал анализа сметы&nbsp;
                </Typography>

                {/* Кнопка входа */}
                <Button
                    variant="contained"
                    size="large"
                    startIcon={<LoginIcon/>}
                    onClick={() => navigate('/login')}
                    sx={{
                        textTransform: 'none',
                        fontWeight: 'bold',
                        fontSize: '1.05rem',
                        px: 5, py: 1.75,
                        borderRadius: 50,
                        bgcolor: 'white',
                        color: '#ffffff',
                        boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
                        transition: 'all 0.3s',
                        animation: 'fadeInUp 0.8s ease-out 0.7s both',
                        '&:hover': {
                            bgcolor: 'white',
                            transform: 'translateY(-2px)',
                            boxShadow: '0 14px 40px rgba(0,0,0,0.35)',
                        },
                    }}
                >
                    Войти в систему
                </Button>
            </Container>

            {/* Футер */}
            <Box sx={{
                position: 'absolute', bottom: 24, left: 0, right: 0,
                textAlign: 'center', zIndex: 1,
            }}>
                <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.6)', letterSpacing: 1}}>
                    © 2026 · Департамент развития внутристрановой ценности
                </Typography>
            </Box>
        </Box>
    );
}
