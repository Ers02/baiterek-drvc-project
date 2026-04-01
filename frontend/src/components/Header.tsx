import React, { useState } from 'react'
import { AppBar, Toolbar, Typography, Button, Box, Select, MenuItem, FormControl, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, Menu } from '@mui/material'
import { useTranslation } from '../i18n'
import { useNavigate, useLocation } from 'react-router-dom'
import { jwtDecode } from 'jwt-decode'
import LogoutIcon from '@mui/icons-material/Logout';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import SettingsIcon from '@mui/icons-material/Settings';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';

export default function Header() {
  const { t, lang, setLang } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [videoModalOpen, setVideoModalOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const token = localStorage.getItem('token');
  let isAdmin = false;
  let userRole = null;
  let hasAdminAccess = false;
  if (token) {
      try {
          const decoded: any = jwtDecode(token);
          isAdmin = decoded.is_admin === true;
          userRole = decoded.role;
          hasAdminAccess = isAdmin || userRole === 'analyst_drvc';
      } catch (e) {}
  }

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleOpenVideoModal = () => {
    setVideoModalOpen(true);
  };

  const handleCloseVideoModal = () => {
    setVideoModalOpen(false);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    handleMenuClose();
  };

  const getPageTitle = () => {
    if (location.pathname === '/admin') return 'Панель администратора';
    if (location.pathname === '/psd-analyst') return 'Аналитика ПСД';
    return t('title');
  }

  return (
    <AppBar position="static" color="primary" elevation={0} sx={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Box display="flex" alignItems="center" gap={3}>
          <Typography
            variant="h6"
            fontWeight="800"
            sx={{ cursor: 'pointer', letterSpacing: '-0.5px' }}
            onClick={() => navigate('/')}
          >
            {t('title')}
          </Typography>

          {hasAdminAccess && (
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 2, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 2, p: 0.5 }}>
              <Button
                color="inherit"
                onClick={handleMenuOpen}
                endIcon={<KeyboardArrowDownIcon />}
                sx={{
                  fontWeight: '600',
                  px: 2,
                  borderRadius: 1.5,
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' }
                }}
              >
                {location.pathname === '/psd-analyst' ? 'Аналитика ПСД' : 'Администрирование'}
              </Button>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
                PaperProps={{
                  sx: { mt: 1, minWidth: 200, boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }
                }}
              >
                <MenuItem onClick={() => handleNavigate('/admin')} selected={location.pathname === '/admin'}>
                  <SettingsIcon sx={{ mr: 1.5, fontSize: 20, color: 'text.secondary' }} />
                  Админка
                </MenuItem>
                <MenuItem onClick={() => handleNavigate('/psd-analyst')} selected={location.pathname === '/psd-analyst'}>
                  <AnalyticsIcon sx={{ mr: 1.5, fontSize: 20, color: 'text.secondary' }} />
                  Аналитика ПСД
                </MenuItem>
              </Menu>
            </Box>
          )}
        </Box>

        <Box display="flex" alignItems="center" gap={1.5}>
          <Tooltip title={t('video_instruction') || "Видеоинструкция"}>
            <IconButton color="inherit" onClick={handleOpenVideoModal} sx={{ bgcolor: 'rgba(255,255,255,0.1)' }}>
              <PlayCircleOutlineIcon />
            </IconButton>
          </Tooltip>

          <FormControl size="small" variant="standard" sx={{ m: 1, minWidth: 60 }}>
            <Select
              value={lang}
              onChange={(e) => setLang(e.target.value as 'ru' | 'kk')}
              disableUnderline
              sx={{
                color: 'white',
                fontWeight: '600',
                '& .MuiSelect-icon': { color: 'white' }
              }}
            >
              <MenuItem value="ru">RU</MenuItem>
              <MenuItem value="kk">KZ</MenuItem>
            </Select>
          </FormControl>

          <Tooltip title={t('logout') || "Выйти"}>
            <IconButton color="inherit" onClick={handleLogout} sx={{ bgcolor: 'rgba(255,255,255,0.1)', ml: 1 }}>
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      <Dialog open={videoModalOpen} onClose={handleCloseVideoModal} maxWidth="md" fullWidth>
        <DialogTitle>{t('video_instruction_title') || "Видеоинструкция"}</DialogTitle>
        <DialogContent>
          <video controls width="100%" src="/Видеоинструкция.mp4">
            {t('video_not_supported') || "Ваш браузер не поддерживает видео."}
          </video>
        </DialogContent>
      </Dialog>
    </AppBar>
  )
}
