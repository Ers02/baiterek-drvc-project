import { useState } from 'react';
import {
  AppBar, Toolbar, Typography, Box, Select, MenuItem, FormControl,
  IconButton, Tooltip, Dialog, DialogTitle, DialogContent,
} from '@mui/material';
import { useTranslation } from '../i18n';
import { useNavigate } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';

export default function TopBar() {
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();
  const [videoModalOpen, setVideoModalOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/welcome');
  };

  return (
    <AppBar position="sticky" color="primary" elevation={0} sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
      <Toolbar sx={{ justifyContent: 'space-between', minHeight: '52px !important', px: { xs: 2, md: 2.5 } }}>
        <Box
          onClick={() => navigate('/')}
          sx={{ display: 'flex', alignItems: 'center', gap: 1.25, cursor: 'pointer', '&:hover': { opacity: 0.9 } }}
        >
          <Box
            component="img"
            src="/baiterek.png"
            alt="Байтерек"
            sx={{ height: 30, width: 'auto', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.25))' }}
            onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
              (e.currentTarget as HTMLImageElement).src = '/baiterek.svg';
            }}
          />
          <Typography variant="subtitle1" fontWeight="700" sx={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}>
            {t('title')}
          </Typography>
        </Box>

        <Box display="flex" alignItems="center" gap={0.5}>
          <Tooltip title={t('video_instruction') || 'Видеоинструкция'}>
            <IconButton
              color="inherit" size="small"
              onClick={() => setVideoModalOpen(true)}
              sx={{ bgcolor: 'rgba(255,255,255,0.10)', '&:hover': { bgcolor: 'rgba(255,255,255,0.20)' } }}
            >
              <PlayCircleOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <FormControl size="small" variant="standard" sx={{ minWidth: 52 }}>
            <Select
              value={lang}
              onChange={e => setLang(e.target.value as 'ru' | 'kk')}
              disableUnderline
              sx={{
                color: 'white', fontWeight: 600,
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
              color="inherit" size="small"
              onClick={handleLogout}
              sx={{ bgcolor: 'rgba(255,255,255,0.10)', '&:hover': { bgcolor: 'rgba(255,255,255,0.20)' } }}
            >
              <LogoutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      <Dialog open={videoModalOpen} onClose={() => setVideoModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('video_instruction_title') || 'Видеоинструкция'}</DialogTitle>
        <DialogContent>
          <video controls width="100%" src="/Видеоинструкция.mp4">
            {t('video_not_supported')}
          </video>
        </DialogContent>
      </Dialog>
    </AppBar>
  );
}
