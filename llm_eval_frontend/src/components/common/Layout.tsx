import React from 'react';
import { Outlet } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, IconButton, Drawer, List, ListItem, ListItemIcon, ListItemText, Divider, useTheme } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import CloudIcon from '@mui/icons-material/Cloud';
import StorageIcon from '@mui/icons-material/Storage';
import AssessmentIcon from '@mui/icons-material/Assessment';
import LeaderboardIcon from '@mui/icons-material/Leaderboard';
import PsychologyIcon from '@mui/icons-material/Psychology';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppContext } from '../../contexts/AppContext';

const drawerWidth = 240;

/**
 * アプリケーションのレイアウトコンポーネント
 */
const Layout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const { darkMode, toggleDarkMode } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  const isActive = (path: string) => {
    return location.pathname.startsWith(path);
  };

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          LLMリーダーボード
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        <ListItem 
          button 
          onClick={() => handleNavigation('/providers')}
          selected={isActive('/providers')}
        >
          <ListItemIcon>
            <CloudIcon color={isActive('/providers') ? 'primary' : undefined} />
          </ListItemIcon>
          <ListItemText primary="プロバイダ" />
        </ListItem>
        <ListItem 
          button 
          onClick={() => handleNavigation('/datasets')}
          selected={isActive('/datasets')}
        >
          <ListItemIcon>
            <StorageIcon color={isActive('/datasets') ? 'primary' : undefined} />
          </ListItemIcon>
          <ListItemText primary="データセット" />
        </ListItem>
        <ListItem 
          button 
          onClick={() => handleNavigation('/metrics')}
          selected={isActive('/metrics')}
        >
          <ListItemIcon>
            <AssessmentIcon color={isActive('/metrics') ? 'primary' : undefined} />
          </ListItemIcon>
          <ListItemText primary="評価" />
        </ListItem>
        <ListItem 
          button 
          onClick={() => handleNavigation('/inferences')}
          selected={isActive('/inferences')}
        >
          <ListItemIcon>
            <PsychologyIcon color={isActive('/inferences') ? 'primary' : undefined} />
          </ListItemIcon>
          <ListItemText primary="推論" />
        </ListItem>
        <ListItem 
          button 
          onClick={() => handleNavigation('/leaderboard')}
          selected={isActive('/leaderboard')}
        >
          <ListItemIcon>
            <LeaderboardIcon color={isActive('/leaderboard') ? 'primary' : undefined} />
          </ListItemIcon>
          <ListItemText primary="リーダーボード" />
        </ListItem>
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            LLMリーダーボード
          </Typography>
          <IconButton color="inherit" onClick={toggleDarkMode}>
            {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="mailbox folders"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{ 
          flexGrow: 1, 
          p: 3, 
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: theme.palette.background.default
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
