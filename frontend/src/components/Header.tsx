import { AppBar, Toolbar, Typography, Button, Box, Select, MenuItem, FormControl } from '@mui/material'
import { useTranslation } from '../i18n'
import { useNavigate } from 'react-router-dom'

export default function Header() {
  const { t, lang, setLang } = useTranslation()
  const navigate = useNavigate()

  return (
    <AppBar position="static" color="primary" elevation={4}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight="bold" sx={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
          {t('title')}
        </Typography>

        <Box display="flex" alignItems="center" gap={3}>
          <FormControl size="small" variant="outlined">
            <Select
              value={lang}
              onChange={(e) => setLang(e.target.value as 'ru' | 'kk')}
              sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'white' }, '& .MuiSvgIcon-root': { color: 'white' } }}
            >
              <MenuItem value="ru">РУС</MenuItem>
              <MenuItem value="kk">ҚАЗ</MenuItem>
            </Select>
          </FormControl>

          <Button color="inherit" onClick={() => navigate('/')}>
            {t('my_procurement_plans')}
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
