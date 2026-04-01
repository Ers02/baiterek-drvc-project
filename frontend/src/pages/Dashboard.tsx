import React, { useEffect, useState, Fragment, useMemo } from 'react';
import {
  Box, Button, Typography, Paper, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, DialogContentText,
  Collapse, Chip, Tooltip, Stack, Tabs, Tab, InputAdornment, Grid, Container
} from '@mui/material';
import {
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon, KeyboardArrowUp as KeyboardArrowUpIcon,
  FileCopy as FileCopyIcon, Download as DownloadIcon, RestoreFromTrash as RestoreFromTrashIcon,
  Visibility as VisibilityIcon, CheckCircle as CheckCircleIcon, Search as SearchIcon,
  AdminPanelSettings as AdminPanelSettingsIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '../i18n/index.tsx';
import Header from '../components/Header';
import {
  getPlans, deletePlan, createPlan, deleteLatestVersion, exportVersionToExcel,
  PlanStatus
} from '../services/api';
import type { ProcurementPlan } from '../services/api';
import { format } from 'date-fns';
import { jwtDecode } from 'jwt-decode';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'KZT', maximumFractionDigits: 0 }).format(amount);

const getStatusChipColor = (status: PlanStatus, isExecuted: boolean) => {
  if (isExecuted) return "success";
  switch (status) {
    case PlanStatus.DRAFT: return "info";
    case PlanStatus.PRE_APPROVED: return "warning";
    case PlanStatus.APPROVED: return "primary";
    default: return "default";
  }
};

const PlanRow = React.memo(({ plan, onReload }: { plan: ProcurementPlan; onReload: () => void; }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [isErrorDialogOpen, setErrorDialogOpen] = useState(false);
  const [errorDialogMessage, setErrorDialogMessage] = useState('');

  const handleError = (err: any, defaultMessage: string) => {
    const message = err.response?.data?.detail || defaultMessage;
    setErrorDialogMessage(message);
    setErrorDialogOpen(true);
  };

  const handleCreateNewVersion = async () => {
    if (window.confirm(t('confirm_create_version'))) {
      try {
        const newVersion = await createVersion(plan.id);
        navigate(`/plans/${newVersion.plan_id}`);
      } catch (err) {
        handleError(err, t('error_creating_version'));
      }
    }
  };

  const handleDeleteLatest = async () => {
    if (window.confirm(t('confirm_delete_version'))) {
      try {
        await deleteLatestVersion(plan.id);
        onReload();
      } catch (err) {
        handleError(err, t('error_deleting_version'));
      }
    }
  };

  const handleDeletePlan = async () => {
    if (window.confirm(t('confirm_delete_plan'))) {
      try {
        await deletePlan(plan.id);
        onReload();
      } catch (err) {
        handleError(err, t('error_deleting_plan'));
      }
    }
  };

  const activeVersion = plan.versions.find(v => v.is_active);
  const canDeletePlan = !plan.versions.some(v => v.status !== PlanStatus.DRAFT);
  const isExecuted = activeVersion?.is_executed || false;

  return (
    <Fragment>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell width="50px">
          <IconButton aria-label="expand row" size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Typography
            variant="subtitle1"
            fontWeight="bold"
            sx={{
                cursor: 'pointer',
                color: 'primary.main',
                '&:hover': { textDecoration: 'underline' }
            }}
            onClick={() => navigate(`/plans/${plan.id}`)}
          >
            {plan.plan_name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {plan.year}
          </Typography>
        </TableCell>
        <TableCell width="150px">
          <Chip
            label={isExecuted ? t('status_EXECUTED') : t(`status_${activeVersion?.status}`)}
            color={getStatusChipColor(activeVersion?.status || PlanStatus.DRAFT, isExecuted)}
            size="small"
            icon={isExecuted ? <CheckCircleIcon /> : undefined}
          />
        </TableCell>
        <TableCell width="180px" align="right">{formatCurrency(activeVersion?.total_amount || 0)}</TableCell>
        <TableCell width="150px" align="right">
          <Stack direction="row" justifyContent="flex-end" spacing={1}>
            {activeVersion?.status === PlanStatus.DRAFT ? (
                <Tooltip title={t('edit_draft')}>
                <IconButton size="small" onClick={() => navigate(`/plans/${plan.id}`)}>
                    <EditIcon />
                </IconButton>
                </Tooltip>
            ) : (
                <Tooltip title={t('view_plan')}>
                <IconButton size="small" onClick={() => navigate(`/plans/${plan.id}`)}>
                    <VisibilityIcon />
                </IconButton>
                </Tooltip>
            )}
            
            {activeVersion?.status !== PlanStatus.DRAFT && (
                <Tooltip title={t('create_new_version_tooltip')}>
                <IconButton size="small" color="primary" onClick={handleCreateNewVersion}>
                    <FileCopyIcon />
                </IconButton>
                </Tooltip>
            )}

            {activeVersion?.status === PlanStatus.DRAFT && activeVersion.version_number > 1 && (
                <Tooltip title={t('delete_draft_version_tooltip')}>
                <IconButton size="small" color="secondary" onClick={handleDeleteLatest}>
                    <RestoreFromTrashIcon />
                </IconButton>
                </Tooltip>
            )}
            {canDeletePlan && (
                <Tooltip title={t('delete_plan_tooltip')}>
                <IconButton size="small" color="error" onClick={handleDeletePlan}>
                    <DeleteIcon />
                </IconButton>
                </Tooltip>
            )}
          </Stack>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Typography variant="h6" gutterBottom component="div">{t('versions_history')}</Typography>
              <Table size="small" aria-label="versions">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('version')}</TableCell>
                    <TableCell>{t('status')}</TableCell>
                    <TableCell align="right">{t('total_amount')}</TableCell>
                    <TableCell>{t('creator')}</TableCell>
                    <TableCell>{t('creation_date')}</TableCell>
                    <TableCell align="right">{t('actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {plan.versions.map((version) => (
                    <TableRow key={version.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight={version.is_active ? "bold" : "normal"}>
                          v{version.version_number} {version.is_active && `(${t('active')})`}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                            label={version.is_executed ? t('status_EXECUTED') : t(`status_${version.status}`)}
                            color={getStatusChipColor(version.status, version.is_executed)} 
                            size="small" 
                        />
                      </TableCell>
                      <TableCell align="right">{formatCurrency(version.total_amount)}</TableCell>
                      <TableCell>{version.creator?.full_name || '-'}</TableCell>
                      <TableCell>{format(new Date(version.created_at), 'dd.MM.yyyy HH:mm')}</TableCell>
                      <TableCell align="right">
                        <Tooltip title={t('export_to_excel')}>
                          <IconButton size="small" onClick={() => exportVersionToExcel(plan.id, version.id)}>
                            <DownloadIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
      <Dialog open={isErrorDialogOpen} onClose={() => setErrorDialogOpen(false)}>
        <DialogTitle>⚠️ {t('error_title')}</DialogTitle>
        <DialogContent><DialogContentText>{errorDialogMessage}</DialogContentText></DialogContent>
        <DialogActions><Button onClick={() => setErrorDialogOpen(false)} autoFocus>{t('close')}</Button></DialogActions>
      </Dialog>
    </Fragment>
  );
});

export default function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<ProcurementPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateDialogOpen, setCreateDialogOpen] = useState(false);
  const [newPlanName, setNewPlanName] = useState('');
  const [newPlanYear, setNewPlanYear] = useState(new Date().getFullYear());
  
  const [currentTab, setCurrentTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Проверка прав админа
  const token = localStorage.getItem('token');
  let isAdmin = false;
  let userRole = null;
  if (token) {
      try {
          const decoded: any = jwtDecode(token);
          isAdmin = decoded.is_admin === true;
          userRole = decoded.role; // Добавляем получение роли
      } catch (e) {}
  }

  const loadPlans = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getPlans();
      // Аналитик ДРВЦ видит все планы в обратном порядке
      setPlans(data.sort((a, b) => b.id - a.id));
    } catch (err) {
      setError(t('error_loading_plans'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, [t]);

  const handleOpenCreateDialog = () => {
    setNewPlanName('');
    setNewPlanYear(new Date().getFullYear());
    setCreateDialogOpen(true);
  };

  const handleCreatePlan = async () => {
    if (!newPlanName.trim()) {
      alert(t('plan_name_required'));
      return;
    }
    try {
      const newPlan = await createPlan({ plan_name: newPlanName, year: newPlanYear });
      setCreateDialogOpen(false);
      navigate(`/plans/${newPlan.id}`);
    } catch (err) {
      setError(t('error_creating_plan'));
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const filteredPlans = useMemo(() => {
    let filtered = plans;

    if (searchQuery) {
        const lowerQuery = searchQuery.toLowerCase();
        filtered = filtered.filter(plan => 
            plan.plan_name.toLowerCase().includes(lowerQuery) || 
            plan.year.toString().includes(lowerQuery)
        );
    }

    if (currentTab === 0) return filtered;

    return filtered.filter(plan => {
        const activeVersion = plan.versions.find(v => v.is_active);
        if (!activeVersion) return false;

        if (currentTab === 4) return activeVersion.is_executed;
        if (activeVersion.is_executed) return false;

        switch (currentTab) {
            case 1: return activeVersion.status === PlanStatus.DRAFT;
            case 2: return activeVersion.status === PlanStatus.PRE_APPROVED;
            case 3: return activeVersion.status === PlanStatus.APPROVED;
            default: return true;
        }
    });
  }, [plans, searchQuery, currentTab]);

  return (
    <>
      <Header />
      <Container maxWidth={false} sx={{ py: 4, px: { xs: 2, md: 4 } }}>
        <Grid container spacing={3} alignItems="center" sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6}>
                <Typography variant="h4" fontWeight="bold">
                    {isAdmin ? t('dashboard_title') : userRole === 'analyst_drvc' ? 'Панель Аналитика ДРВЦ' : t('dashboard_title')}
                </Typography>
            </Grid>
            <Grid item xs={12} sm={6} sx={{ display: 'flex', justifyContent: { xs: 'flex-start', sm: 'flex-end' } }}>
                {isAdmin ? (
                    <Button 
                        variant="contained" 
                        color="secondary"
                        startIcon={<AdminPanelSettingsIcon />} 
                        onClick={() => navigate('/admin')}
                    >
                        Перейти в админку
                    </Button>
                ) : (
                    <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreateDialog}>
                        {t('create_plan')}
                    </Button>
                )}
            </Grid>
        </Grid>

        <Paper sx={{ mb: 3, p: 2 }}>
            <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={4}>
                    <TextField
                        fullWidth
                        size="small"
                        variant="outlined"
                        placeholder={t('search_plans_placeholder')}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon color="action" />
                                </InputAdornment>
                            ),
                        }}
                    />
                </Grid>
                <Grid item xs={12} md={8}>
                    <Tabs 
                        value={currentTab} 
                        onChange={handleTabChange} 
                        indicatorColor="primary" 
                        textColor="primary"
                        variant="fullWidth"
                        sx={{ '& .MuiTab-root': { flexGrow: 1, maxWidth: 'none' } }}
                    >
                        <Tab label={t('all_plans')} />
                        <Tab label={t('status_DRAFT')} />
                        <Tab label={t('status_PRE_APPROVED')} />
                        <Tab label={t('status_APPROVED')} />
                        <Tab label={t('status_EXECUTED')} />
                    </Tabs>
                </Grid>
            </Grid>
        </Paper>

        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}
        {error && !loading && <Alert severity="error">{error}</Alert>}

        {!loading && !error && (
          <TableContainer component={Paper}>
            <Table aria-label="collapsible table">
              <TableHead>
                <TableRow>
                  <TableCell width="50px" />
                  <TableCell>{t('plan_details')}</TableCell>
                  <TableCell width="150px">{t('current_status')}</TableCell>
                  <TableCell width="180px" align="right">{t('active_version_amount')}</TableCell>
                  <TableCell width="150px" align="right">{t('actions')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredPlans.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" sx={{ p: 3 }}>
                        {t('no_plans_found')}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredPlans.map(plan => <PlanRow key={plan.id} plan={plan} onReload={loadPlans} />)
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Container>

      <Dialog open={isCreateDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('create_new_plan_title')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{pt: 1}}>
            <TextField
              autoFocus
              required
              margin="dense"
              label={t('plan_name')}
              type="text"
              fullWidth
              variant="outlined"
              value={newPlanName}
              onChange={(e) => setNewPlanName(e.target.value)}
              inputProps={{ maxLength: 80 }}
            />
            <TextField
              required
              margin="dense"
              label={t('plan_year')}
              type="number"
              fullWidth
              variant="outlined"
              value={newPlanYear}
              onChange={(e) => setNewPlanYear(Number(e.target.value))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>{t('cancel')}</Button>
          <Button onClick={handleCreatePlan}>{t('create_button')}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
