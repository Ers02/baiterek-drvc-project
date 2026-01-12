import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Paper, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Chip, Stack, Container, Tooltip
} from '@mui/material';
import {
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
  LockOpen as LockOpenIcon, CheckCircle as CheckCircleIcon, Download as DownloadIcon,
  Undo as UndoIcon, Assignment as AssignmentIcon, FileCopy as FileCopyIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon, Upload as UploadIcon
} from '@mui/icons-material';
import { useTranslation } from '../i18n/index.tsx';
import Header from '../components/Header';
import ExecutionModal from '../components/ExecutionModal';
import ImportModal from '../components/ImportModal';
import {
  getPlanById, deleteItem, updateVersionStatus, exportVersionToExcel, revertItem, createVersion,
  PlanStatus
} from '../services/api';
import type { ProcurementPlan, ProcurementPlanVersion, PlanItemVersion } from '../services/api';

// ОПТИМИЗАЦИЯ: Создаем форматтер один раз вне компонента
const currencyFormatter = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'KZT' });
const formatCurrency = (amount: number) => currencyFormatter.format(amount);

// Card for displaying statistics
const StatsCard = ({ title, value, color = 'text.primary' }: { title: string; value: React.ReactNode; color?: string; }) => (
  <Paper elevation={1} sx={{ p: 3, textAlign: 'center', height: '100%' }}>
    <Typography variant="h5" sx={{ color, fontWeight: 'bold', mb: 1 }}>{value}</Typography>
    <Typography variant="body2" color="text.secondary">{title}</Typography>
  </Paper>
);

// Section for displaying plan statistics
const StatsSection = ({ version }: { version: ProcurementPlanVersion | null }) => {
  const { t } = useTranslation();
  
  if (!version) {
    return null;
  }

  const ktpPercentage = Number(version.ktp_percentage ?? 0);
  const importPercentage = Number(version.import_percentage ?? 0);
  const totalAmount = Number(version.total_amount ?? 0);
  
  // Новые показатели ВЦ
  const vcMean = Number(version.vc_mean ?? 0);
  const vcMedian = Number(version.vc_median ?? 0);
  const vcAmount = Number(version.vc_amount ?? 0);

  return (
    <Box sx={{ mt: 4, mb: 2 }}>
        {/* Основные показатели */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2, mb: 2 }}>
            <StatsCard title={t('ktp_share')} value={`${ktpPercentage.toFixed(2)}%`} color="success.main" />
            <StatsCard title={t('import_share')} value={`${importPercentage.toFixed(2)}%`} color="error.main" />
            <StatsCard title={t('total_amount')} value={formatCurrency(totalAmount)} color="info.main" />
        </Box>
        
        {/* Показатели ВЦ */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2 }}>
            <StatsCard title={t('vc_mean')} value={`${vcMean.toFixed(2)}%`} color="primary.main" />
            <StatsCard title={t('vc_median')} value={`${vcMedian.toFixed(2)}%`} color="primary.main" />
            <StatsCard title={t('vc_amount')} value={formatCurrency(vcAmount)} color="primary.main" />
        </Box>
    </Box>
  );
};

// Chip for displaying status
const StatusChip = ({ status, isExecuted }: { status: PlanStatus, isExecuted: boolean }) => {
  const { t } = useTranslation();
  
  if (isExecuted) {
      return <Chip label={t('status_EXECUTED')} color="success" variant="outlined" sx={{ fontWeight: 'bold' }} icon={<CheckCircleIcon />} />;
  }

  const statusMap = {
    [PlanStatus.DRAFT]: { label: t('status_DRAFT'), color: 'info' },
    [PlanStatus.PRE_APPROVED]: { label: t('status_PRE_APPROVED'), color: 'warning' },
    [PlanStatus.APPROVED]: { label: t('status_APPROVED'), color: 'primary' },
  };
  const { label, color } = statusMap[status] || statusMap.DRAFT;
  return <Chip label={label} color={color as any} variant="outlined" sx={{ fontWeight: 'bold' }} />;
};

// Функция для форматирования номера позиции
const formatItemNumber = (item: PlanItemVersion) => {
    let number = `${item.item_number}`;
    
    // Используем revision_number для отображения номера редакции
    if (item.revision_number > 0) {
        number += `-${item.revision_number}`;
    }

    // Добавляем тип потребности
    switch (item.need_type) {
        case 'Товар': number += ' Т'; break;
        case 'Работа': number += ' Р'; break;
        case 'Услуга': number += ' У'; break;
    }
    
    return number;
};

// ОПТИМИЗАЦИЯ: Выносим строку таблицы в отдельный мемоизированный компонент
const PlanItemRow = React.memo(({ 
    item, 
    activeVersionId, 
    isEditable, 
    isApproved, 
    t, 
    onEdit, 
    onDelete, 
    onRevert, 
    onExecution 
}: {
    item: PlanItemVersion;
    activeVersionId: number;
    isEditable: boolean;
    isApproved: boolean;
    t: (key: string) => string;
    onEdit: (id: number) => void;
    onDelete: (id: number) => void;
    onRevert: (id: number) => void;
    onExecution: (item: PlanItemVersion) => void;
}) => {
    const canRevert = isEditable && !item.is_deleted && item.source_version_id === activeVersionId && item.root_item_id !== item.id;
    
    const executedQty = Number(item.executed_quantity || 0);
    const planQty = Number(item.quantity || 0);
    const executedAmt = Number(item.executed_amount || 0);
    const planAmt = Number(item.total_amount || 0);
    
    const progress = planQty > 0 ? Math.min((executedQty / planQty) * 100, 100) : 0;
    const isFullyExecuted = executedQty >= planQty && planQty > 0;

    return (
        <TableRow 
            hover
            sx={{
            backgroundColor: item.is_deleted ? '#f5f5f5' : 'inherit',
            '& .MuiTableCell-root': {
                color: item.is_deleted ? 'text.disabled' : 'inherit',
                textDecoration: item.is_deleted ? 'line-through' : 'none',
            },
            }}
        >
            <TableCell>{formatItemNumber(item)}</TableCell>
            <TableCell>{item.enstru?.name_ru || t('no_name')}</TableCell>
            <TableCell>
            <Chip label={item.is_ktp ? t('yes') : t('no')} color={item.is_ktp ? "success" : "default"} size="small" disabled={item.is_deleted} />
            </TableCell>
            <TableCell align="right">{item.quantity}</TableCell>
            <TableCell align="right">{formatCurrency(item.price_per_unit)}</TableCell>
            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatCurrency(item.total_amount)}</TableCell>
            
            {/* Колонка Мин. ВЦ % */}
            <TableCell align="center">
                {item.min_dvc_percent ? `${Number(item.min_dvc_percent).toFixed(2)}%` : '-'}
            </TableCell>
            
            {isApproved && (
                <TableCell align="center">
                {!item.is_deleted ? (
                    <Tooltip 
                        title={
                            <Box>
                                <Typography variant="caption" display="block">{t('quantity')}: {executedQty} / {planQty}</Typography>
                                <Typography variant="caption" display="block">{t('sum')}: {formatCurrency(executedAmt)} / {formatCurrency(planAmt)}</Typography>
                            </Box>
                        }
                    >
                        <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                            {isFullyExecuted ? (
                                <CheckCircleIcon color="success" />
                            ) : executedQty > 0 ? (
                                <CircularProgress variant="determinate" value={progress} size={24} />
                            ) : (
                                <RadioButtonUncheckedIcon color="disabled" />
                            )}
                        </Box>
                    </Tooltip>
                ) : (
                    "-"
                )}
                </TableCell>
            )}

            <TableCell align="center">
            {!item.is_deleted && (
                <Stack direction="row" justifyContent="center" spacing={1}>
                {isEditable && (
                    <>
                    <Tooltip title={t('edit_item')}>
                        <IconButton size="small" onClick={() => onEdit(item.id)} color="primary">
                        <EditIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                    {canRevert && (
                        <Tooltip title={t('revert_item')}>
                        <IconButton size="small" onClick={() => onRevert(item.id)} color="warning">
                            <UndoIcon fontSize="small" />
                        </IconButton>
                        </Tooltip>
                    )}
                    <Tooltip title={t('delete_item')}>
                        <IconButton size="small" onClick={() => onDelete(item.id)} color="error">
                        <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                    </>
                )}
                {isApproved && (
                    <Tooltip title={t('execution_report')}>
                    <IconButton size="small" onClick={() => onExecution(item)} color="info">
                        <AssignmentIcon fontSize="small" />
                    </IconButton>
                    </Tooltip>
                )}
                </Stack>
            )}
            </TableCell>
        </TableRow>
    );
});

export default function PlanForm() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [plan, setPlan] = useState<ProcurementPlan | null>(null);
  const [activeVersion, setActiveVersion] = useState<ProcurementPlanVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isConfirmOpen, setConfirmOpen] = useState(false);
  const [nextStatus, setNextStatus] = useState<PlanStatus | null>(null);
  
  // State for Execution Modal
  const [isExecutionModalOpen, setExecutionModalOpen] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [selectedItemName, setSelectedItemName] = useState('');
  const [selectedItemQuantity, setSelectedItemQuantity] = useState(0);
  const [selectedItemAmount, setSelectedItemAmount] = useState(0);
  const [selectedItemPrice, setSelectedItemPrice] = useState(0);

  // State for Import Modal
  const [isImportModalOpen, setImportModalOpen] = useState(false);

  const loadPlan = useCallback(async () => {
    if (!planId) return;
    try {
      setLoading(true);
      const data = await getPlanById(Number(planId));
      const activeVer = data.versions.find(v => v.is_active);
      setPlan(data);
      setActiveVersion(activeVer || null);
    } catch (err) {
      setError(t('error_loading_plan'));
    } finally {
      setLoading(false);
    }
  }, [planId, t]);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const handleStatusChange = async () => {
    if (!planId || !nextStatus) return;
    try {
      await updateVersionStatus(Number(planId), nextStatus);
      await loadPlan();
    } catch (err: any) {
      setError(`Ошибка: ${err.response?.data?.detail || err.message}`);
    } finally {
      setConfirmOpen(false);
      setNextStatus(null);
    }
  };

  const handleExport = async () => {
    if (!planId || !activeVersion) return;
    try {
      await exportVersionToExcel(Number(planId), activeVersion.id);
    } catch {
      setError(t('error_exporting_excel'));
    }
  };

  const handleCreateNewVersion = async () => {
    if (!planId) return;
    if (window.confirm(t('confirm_create_version'))) {
      setLoading(true);
      try {
        const newVersion = await createVersion(Number(planId));
        await loadPlan();
      } catch (err: any) {
        setError(err.response?.data?.detail || t('error_creating_version'));
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDeleteItem = useCallback(async (itemId: number) => {
    if (window.confirm(t('confirm_delete_item'))) {
      try {
        await deleteItem(itemId);
        loadPlan();
      } catch {
        setError(t('error_deleting_item'));
      }
    }
  }, [t, loadPlan]);

  const handleRevertItem = useCallback(async (itemId: number) => {
    if (window.confirm(t('confirm_revert_item'))) {
      try {
        await revertItem(itemId);
        loadPlan();
      } catch (err: any) {
        const message = err.response?.data?.detail || t('error_reverting_item');
        setError(message);
      }
    }
  }, [t, loadPlan]);

  const handleEditItem = useCallback((itemId: number) => {
      navigate(`/items/${itemId}/edit`);
  }, [navigate]);

  const openConfirmDialog = (status: PlanStatus) => {
    setNextStatus(status);
    setConfirmOpen(true);
  };

  const openExecutionModal = useCallback((item: PlanItemVersion) => {
    setSelectedItemId(item.id);
    setSelectedItemName(item.enstru?.name_ru || '');
    setSelectedItemQuantity(Number(item.quantity));
    setSelectedItemAmount(Number(item.total_amount));
    setSelectedItemPrice(Number(item.price_per_unit));
    setExecutionModalOpen(true);
  }, []);

  const isEditable = activeVersion?.status === PlanStatus.DRAFT;
  const isApproved = activeVersion?.status === PlanStatus.APPROVED;

  const sortedItems = useMemo(() => {
    if (!activeVersion?.items) return [];
    return [...activeVersion.items].sort((a, b) => {
      if (a.is_deleted && !b.is_deleted) return 1;
      if (!a.is_deleted && b.is_deleted) return -1;
      return a.item_number - b.item_number;
    });
  }, [activeVersion]);

  if (loading) return <><Header /><Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box></>;
  if (error) return <><Header /><Box sx={{ p: 4 }}><Alert severity="error">{error}</Alert></Box></>;
  if (!plan || !activeVersion) return <><Header /><Box sx={{ p: 4 }}><Alert severity="info">{t('no_plan_data')}</Alert></Box></>;

  return (
    <>
      <Header />
      <Container maxWidth={false} sx={{ py: 4, px: { xs: 2, md: 4 } }}>
        <Paper sx={{ p: 3, mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" fontWeight="bold" gutterBottom>
              {plan.plan_name}
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="body1" color="text.secondary">
                  {plan.year}
              </Typography>
              <StatusChip status={activeVersion.status} isExecuted={activeVersion.is_executed} />
              <Typography variant="subtitle1" color="text.secondary">
                (v{activeVersion.version_number})
              </Typography>
            </Stack>
          </Box>
          <Stack direction="row" spacing={2}>
            {isEditable && (
                <Button 
                    variant="outlined" 
                    startIcon={<UploadIcon />} 
                    onClick={() => setImportModalOpen(true)}
                >
                    {t('import_items')}
                </Button>
            )}
            <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleExport}>
              {t('export_to_excel')}
            </Button>
            
            {!isEditable && (
                <Button 
                    variant="outlined" 
                    color="primary" 
                    startIcon={<FileCopyIcon />} 
                    onClick={handleCreateNewVersion}
                >
                    {t('create_new_version')}
                </Button>
            )}

            {activeVersion.status === PlanStatus.DRAFT && (
              <Button variant="contained" color="warning" startIcon={<LockOpenIcon />} onClick={() => openConfirmDialog(PlanStatus.PRE_APPROVED)}>
                {t('pre_approve')}
              </Button>
            )}
            {activeVersion.status === PlanStatus.PRE_APPROVED && (
              <Button variant="contained" color="success" startIcon={<CheckCircleIcon />} onClick={() => openConfirmDialog(PlanStatus.APPROVED)}>
                {t('approve_final')}
              </Button>
            )}
          </Stack>
        </Paper>

        <StatsSection version={activeVersion} />

        <Box sx={{ mt: 5 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2} px={2}>
            <Typography variant="h5" fontWeight="500">
              {t('plan_items_title')} ({activeVersion.items?.filter(it => !it.is_deleted).length || 0})
            </Typography>
            {isEditable && (
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate(`/plans/${planId}/items/new`)}>
                {t('add_item')}
              </Button>
            )}
          </Stack>

          <Paper sx={{ width: '100%', overflow: 'hidden', mb: 4 }}>
            <TableContainer sx={{ maxHeight: 600 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>№</TableCell>
                    <TableCell>{t('item_name')}</TableCell>
                    <TableCell>{t('is_ktp')}</TableCell>
                    <TableCell align="right">{t('item_quantity')}</TableCell>
                    <TableCell align="right">{t('item_price')}</TableCell>
                    <TableCell align="right">{t('total_amount')}</TableCell>
                    <TableCell align="center">{t('min_dvc_percent')}</TableCell>
                    {isApproved && <TableCell align="center">{t('status')}</TableCell>}
                    <TableCell align="center">{t('actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedItems.length > 0 ? (
                    sortedItems.map((item) => (
                        <PlanItemRow 
                            key={item.id}
                            item={item}
                            activeVersionId={activeVersion.id}
                            isEditable={isEditable}
                            isApproved={isApproved}
                            t={t}
                            onEdit={handleEditItem}
                            onDelete={handleDeleteItem}
                            onRevert={handleRevertItem}
                            onExecution={openExecutionModal}
                        />
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={isApproved ? 9 : 8} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">{t('no_items_in_plan')}</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Box>
      </Container>

      <Dialog open={isConfirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>{t('confirm_status_change_title')}</DialogTitle>
        <DialogContent><DialogContentText>{t('confirm_status_change_body')}</DialogContentText></DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>{t('cancel')}</Button>
          <Button onClick={handleStatusChange} variant="contained" autoFocus>{t('confirm')}</Button>
        </DialogActions>
      </Dialog>
      
      {selectedItemId && (
        <ExecutionModal 
          open={isExecutionModalOpen}
          onClose={() => {
              setExecutionModalOpen(false);
              loadPlan(); 
          }}
          itemId={selectedItemId}
          itemName={selectedItemName}
          planQuantity={selectedItemQuantity}
          planAmount={selectedItemAmount}
          planPricePerUnit={selectedItemPrice}
        />
      )}

      {planId && (
        <ImportModal 
            open={isImportModalOpen}
            onClose={() => setImportModalOpen(false)}
            planId={Number(planId)}
            onSuccess={loadPlan}
        />
      )}
    </>
  );
}
