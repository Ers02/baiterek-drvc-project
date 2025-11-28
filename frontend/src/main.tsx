import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { LangProvider } from './i18n'

const theme = createTheme({
  palette: {
    primary: {
      main: '#1B5E20', // тёмно-зелёный
      light: '#4CAF50',
      dark: '#003300',
    },
    secondary: {
      main: '#8BC34A',
    },
    background: {
      default: '#E8F5E9',
      paper: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Arial", sans-serif',
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LangProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </LangProvider>
  </React.StrictMode>,
)