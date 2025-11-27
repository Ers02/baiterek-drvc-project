// src/components/Header.tsx
import { AppBar, Toolbar, Typography, Button, Box, ToggleButton, ToggleButtonGroup } from '@mui/material'
import { useLang } from '../i18n'

export default function Header() {
  const [lang, changeLang] = useLang()

  return (
    <AppBar position="static" color="primary" elevation={4}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight="bold">
          Портал финансирования
        </Typography>

        <Box display="flex" alignItems="center" gap={3}>
          <ToggleButtonGroup size="small" exclusive value={lang} onChange={(_, v) => v && changeLang(v)}>
            <ToggleButton value="ru">РУС</ToggleButton>
            <ToggleButton value="kk">ҚАЗ</ToggleButton>
          </ToggleButtonGroup>

          <Button color="inherit" href="/applications/new">
            {lang === 'ru' ? 'Новая заявка' : 'Жаңа өтініш'}
          </Button>
          <Button color="inherit" href="/">
            {lang === 'ru' ? 'Мои заявки' : 'Менің өтініштерім'}
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}