import { useState } from 'react'
import { AppBar, Toolbar, Typography, Box, Select, MenuItem, FormControl, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, Button } from '@mui/material'
import { useTranslation } from '../i18n'
import { useNavigate, useLocation } from 'react-router-dom'
import LogoutIcon from '@mui/icons-material/Logout';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import DashboardIcon from '@mui/icons-material/Dashboard';
import FilterListIcon from '@mui/icons-material/FilterList';
import { jwtDecode } from 'jwt-decode';

export default function Header() {
  const { t, lang, setLang } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [videoModalOpen, setVideoModalOpen] = useState(false);

  const token = localStorage.getItem('token');
  let isAdminOrAnalyst = false;
  let isDirector = false;
  if (token) {
    try {
      const decoded: { is_admin?: boolean; role?: string; is_director?: boolean } = jwtDecode(token);
      isAdminOrAnalyst = decoded.is_admin === true || decoded.role === 'analyst_drvc';
      isDirector = decoded.role === 'director_drvc' || decoded.is_director === true;
    } catch { /* ignore */ }
  }
  const showAnalystMenu = isAdminOrAnalyst || isDirector;

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/welcome');
  };

  const handleOpenVideoModal = () => {
    setVideoModalOpen(true);
  };

  const handleCloseVideoModal = () => {
    setVideoModalOpen(false);
  };

  return (
    <AppBar position="static" color="primary" elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between', minHeight: 64, px: { xs: 2, md: 3 } }}>
        <Box display="flex" alignItems="center" gap={3}>
          <Box
            onClick={() => navigate('/')}
            sx={{
              display: 'flex', alignItems: 'center', gap: 1.25,
              cursor: 'pointer',
              transition: 'opacity 0.2s',
              '&:hover': { opacity: 0.9 },
            }}
          >
            <Box
              component="img"
              src="/baiterek.png"
              alt="Байтерек"
              sx={{ height: 36, width: 'auto', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.25))' }}
              onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                (e.currentTarget as HTMLImageElement).src = '/baiterek.svg';
              }}
            />
            <Typography
              variant="h6"
              fontWeight="700"
              sx={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}
            >
              {t('title')}
            </Typography>
          </Box>

          {showAnalystMenu && (
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Button
                color="inherit"
                size="small"
                startIcon={<DashboardIcon />}
                onClick={() => navigate('/psd-analyst')}
                sx={{
                  textTransform: 'none',
                  fontWeight: 600,
                  px: 1.5, py: 0.75,
                  borderRadius: 2,
                  bgcolor: location.pathname === '/psd-analyst' ? 'rgba(255,255,255,0.18)' : 'transparent',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.12)' },
                }}
              >
                Аналитика
              </Button>
              <Button
                color="inherit"
                size="small"
                startIcon={<FilterListIcon />}
                onClick={() => navigate('/ktp-search')}
                sx={{
                  textTransform: 'none',
                  fontWeight: 600,
                  px: 1.5, py: 0.75,
                  borderRadius: 2,
                  bgcolor: location.pathname === '/ktp-search' ? 'rgba(255,255,255,0.18)' : 'transparent',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.12)' },
                }}
              >
                Поиск КТП
              </Button>
            </Box>
          )}
        </Box>

        <Box display="flex" alignItems="center" gap={1}>
          <Tooltip title={t('video_instruction') || "Видеоинструкция"}>
            <IconButton
              color="inherit"
              onClick={handleOpenVideoModal}
              sx={{
                bgcolor: 'rgba(255,255,255,0.10)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.20)' },
              }}
            >
              <PlayCircleOutlineIcon />
            </IconButton>
          </Tooltip>

          <FormControl size="small" variant="standard" sx={{ minWidth: 56 }}>
            <Select
              value={lang}
              onChange={(e) => setLang(e.target.value as 'ru' | 'kk')}
              disableUnderline
              sx={{
                color: 'white',
                fontWeight: 600,
                '& .MuiSelect-icon': { color: 'white' },
                '& .MuiSelect-select': { py: 0.5, px: 1 },
              }}
            >
              <MenuItem value="ru">RU</MenuItem>
              <MenuItem value="kk">KZ</MenuItem>
            </Select>
          </FormControl>

          <Tooltip title={t('logout')}>
            <IconButton
              color="inherit"
              onClick={handleLogout}
              sx={{
                bgcolor: 'rgba(255,255,255,0.10)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.20)' },
              }}
            >
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      <Dialog open={videoModalOpen} onClose={handleCloseVideoModal} maxWidth="md" fullWidth>
        <DialogTitle>{t('video_instruction_title') || "Видеоинструкция"}</DialogTitle>
        <DialogContent>
          <video controls width="100%" src="/Видеоинструкция.mp4">
            {t('video_not_supported')}
          </video>
        </DialogContent>
      </Dialog>
    </AppBar>
  )
}
