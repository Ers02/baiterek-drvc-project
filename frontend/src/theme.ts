import { createTheme } from '@mui/material/styles';

/**
 * Единая цветовая палитра приложения.
 * Оттенки согласованы с Welcome/Login страницами:
 *   #062f1d → #0b4b32 → #116745 (тёмный → средний → светлый зелёный).
 */
const COLORS = {
  primary:      '#0b4b32', // основной (заголовки, кнопки, активные иконки)
  primaryDark:  '#062f1d', // тёмный (hover, тени)
  primaryLight: '#116745', // светлый (градиенты)
  secondary:    '#4caf50', // акцент (chip, badge)
  accent:       '#a5d6a7', // светлый акцент (hover-фон)
  bg:           '#f7faf8', // мягкий нейтрально-зелёный фон страниц
};

const theme = createTheme({
  palette: {
    primary: {
      main: COLORS.primary,
      light: COLORS.primaryLight,
      dark: COLORS.primaryDark,
      contrastText: '#ffffff',
    },
    secondary: {
      main: COLORS.secondary,
      light: COLORS.accent,
    },
    background: {
      default: COLORS.bg,
      paper: '#ffffff',
    },
    success: {
      main: '#2e7d32',
      light: '#a5d6a7',
    },
    text: {
      primary: '#1b1f1c',
      secondary: '#52635b',
    },
    divider: 'rgba(11,75,50,0.10)',
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Arial", sans-serif',
    h4: { fontWeight: 700, fontSize: '1.75rem' },
    h5: { fontWeight: 600, fontSize: '1.5rem' },
    h6: { fontWeight: 600, fontSize: '1.15rem' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: `linear-gradient(135deg, ${COLORS.primaryDark} 0%, ${COLORS.primary} 60%, ${COLORS.primaryLight} 100%)`,
          boxShadow: '0 4px 20px rgba(6,47,29,0.20)',
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 600,
        },
        containedPrimary: {
          background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.primaryLight} 100%)`,
          boxShadow: '0 4px 12px rgba(11,75,50,0.25)',
          '&:hover': {
            background: `linear-gradient(135deg, ${COLORS.primaryDark} 0%, ${COLORS.primary} 100%)`,
            boxShadow: '0 6px 18px rgba(11,75,50,0.35)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 12 },
        elevation1: { boxShadow: '0 2px 12px rgba(11,75,50,0.06)' },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(11,75,50,0.06)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: COLORS.primaryLight,
            borderWidth: 1.5,
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          fontSize: '0.875rem',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 700,
            color: COLORS.primaryDark,
            backgroundColor: 'rgba(11,75,50,0.04)',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: 14 },
      },
    },
  },
});

export default theme;
