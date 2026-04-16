import React, { useState } from 'react'
import { AppBar, Toolbar, Typography, Box, Select, MenuItem, FormControl, IconButton, Tooltip, Dialog, DialogTitle, DialogContent } from '@mui/material'
import { useTranslation } from '../i18n'
import { useNavigate } from 'react-router-dom'
import LogoutIcon from '@mui/icons-material/Logout';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';

export default function Header() {
  const { t, lang, setLang } = useTranslation()
  const navigate = useNavigate()
  const [videoModalOpen, setVideoModalOpen] = useState(false);

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
