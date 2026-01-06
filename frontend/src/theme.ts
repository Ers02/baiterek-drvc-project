import { createTheme } from '@mui/material/styles';

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
    h4: {
      fontWeight: 700,
      fontSize: '1.75rem', // ~28px
    },
    h5: {
      fontWeight: 500,
      fontSize: '1.5rem', // ~24px
    },
  },
});

export default theme;
