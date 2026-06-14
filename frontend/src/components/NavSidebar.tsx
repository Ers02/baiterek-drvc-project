import { useState } from 'react';
import {
  Drawer, Box, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Tooltip, IconButton, Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Inbox as InboxIcon,
  Assignment as AssignmentIcon,
  Search as SearchIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';

const DRAWER_WIDTH = 220;
const DRAWER_MINI = 60;

const NAV_ITEMS = [
  { label: 'Дашборд',   icon: <DashboardIcon />,  path: '/',             adminOnly: false },
  { label: 'Проекты',   icon: <InboxIcon />,       path: '/admin',        adminOnly: true  },
  { label: 'ПСД Анализ',icon: <AssignmentIcon />,  path: '/psd-analyst',  adminOnly: true  },
  { label: 'Поиск КТП', icon: <SearchIcon />,      path: '/ktp-search',   adminOnly: true  },
];

function hasAdminAccess(): boolean {
  const token = localStorage.getItem('token');
  if (!token) return false;
  try {
    const decoded: { is_admin?: boolean; role?: string } = jwtDecode(token);
    return (
      decoded.is_admin === true ||
      decoded.role === 'ANALYST_DRVC' ||
      decoded.role === 'DIRECTOR_DRVC' ||
      decoded.role === 'ANALYST_MANAGER'
    );
  } catch {
    return false;
  }
}

export default function NavSidebar() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const canSeeAdminItems = hasAdminAccess();

  // «Дашборд» (adminOnly:false) — только для USER; остальные пункты — для adminish-ролей
  const visibleItems = NAV_ITEMS.filter(item =>
    item.adminOnly ? canSeeAdminItems : !canSeeAdminItems
  );
  const drawerWidth = open ? DRAWER_WIDTH : DRAWER_MINI;

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          overflowX: 'hidden',
          transition: theme => theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: open
              ? theme.transitions.duration.enteringScreen
              : theme.transitions.duration.leavingScreen,
          }),
          boxSizing: 'border-box',
          bgcolor: 'background.paper',
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      {/* Spacer to push items below TopBar */}
      <Box sx={{ height: 52 }} />

      <List sx={{ flex: 1, px: 0.5, pt: 1 }}>
        {visibleItems.map(item => {
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);

          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={open ? '' : item.label} placement="right" arrow>
                <ListItemButton
                  onClick={() => navigate(item.path)}
                  sx={{
                    borderRadius: 2,
                    minHeight: 44,
                    px: open ? 2 : 1.5,
                    justifyContent: open ? 'flex-start' : 'center',
                    bgcolor: isActive ? 'primary.main' : 'transparent',
                    color: isActive ? 'primary.contrastText' : 'text.secondary',
                    '&:hover': {
                      bgcolor: isActive ? 'primary.dark' : 'action.hover',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: open ? 36 : 0,
                      color: 'inherit',
                      justifyContent: 'center',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  {open && (
                    <ListItemText
                      primary={item.label}
                      primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: isActive ? 600 : 400 }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
      </List>

      <Divider />
      <Box sx={{ display: 'flex', justifyContent: open ? 'flex-end' : 'center', p: 0.5 }}>
        <IconButton size="small" onClick={() => setOpen(prev => !prev)}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Box>
    </Drawer>
  );
}
