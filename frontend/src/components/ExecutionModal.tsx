import React, {useState, useEffect, useMemo, useCallback, useRef} from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    TextField, Typography, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, IconButton, Box, Alert, LinearProgress, Stack, CircularProgress, Autocomplete, Link,
    Grid, Card, CardContent, Divider, InputAdornment, Chip, Tooltip
} from '@mui/material';
import {
    Delete as DeleteIcon, 
    Add as AddIcon, 
    Edit as EditIcon, 
    Refresh as RefreshIcon,
    Business as BusinessIcon,
    Description as ContractIcon,
    LocalShipping as SupplyIcon,
    Percent as PercentIcon,
    AttachMoney as MoneyIcon,
    CalendarToday as DateIcon,
    Numbers as NumberIcon,
    Search as SearchIcon,
    Description as DescriptionIcon
} from '@mui/icons-material';
import {useTranslation} from '../i18n/index.tsx';
import {createExecution, getExecutionsByItem, deleteExecution, getSupplierByBin} from '../services/api';
import type {Execution, ExecutionPayload, KtpSupplier} from '../services/api';

interface ExecutionModalProps {
    open: boolean;
    onClose: () => void;
    itemId: number;
    itemName: string;
    planQuantity: number;
    planAmount: number;
    planPricePerUnit: number;
    trucode: string;
    needType: string;
}

const formatMoney = (val: number) => new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'KZT', maximumFractionDigits: 2}).format(val);
const formatNumber = (val: number) => new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 3}).format(val);

// --- Компонент сводки (Дашборд) ---
const ExecutionSummary = ({ planQty, planAmt, execQty, execAmt, t }: { planQty: number, planAmt: number, execQty: number, execAmt: number, t: any }) => {
    const qtyPercent = Math.min((execQty / planQty) * 100, 100);
    const amtPercent = Math.min((execAmt / planAmt) * 100, 100);
    const remainingQty = planQty - execQty;
    const remainingAmt = planAmt - execAmt;

    return (
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 3 }}>
            <Card variant="outlined" sx={{ bgcolor: '#f8faff', flex: 1 }}>
                <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2" color="text.secondary" fontWeight="bold">
                            {t('quantity_progress')} (Факт поставки)
                        </Typography>
                        <Chip 
                            label={`${qtyPercent.toFixed(1)}%`} 
                            size="small" 
                            color={qtyPercent >= 100 ? "success" : "primary"} 
                            variant={qtyPercent >= 100 ? "filled" : "outlined"}
                        />
                    </Stack>
                    <LinearProgress 
                        variant="determinate" 
                        value={qtyPercent} 
                        sx={{ height: 8, borderRadius: 4, mb: 1 }} 
                        color={execQty > planQty ? "error" : "primary"}
                    />
                    <Stack direction="row" justifyContent="space-between">
                        <Typography variant="caption">
                            Факт: <b>{formatNumber(execQty)}</b> / {formatNumber(planQty)}
                        </Typography>
                        <Typography variant="caption" color={remainingQty < 0 ? "error.main" : "text.secondary"}>
                            Остаток: {formatNumber(remainingQty)}
                        </Typography>
                    </Stack>
                </CardContent>
            </Card>
            <Card variant="outlined" sx={{ bgcolor: '#f8faff', flex: 1 }}>
                <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2" color="text.secondary" fontWeight="bold">
                            {t('amount_progress')} (Факт поставки)
                        </Typography>
                        <Chip 
                            label={`${amtPercent.toFixed(1)}%`} 
                            size="small" 
                            color={amtPercent >= 100 ? "success" : "primary"} 
                            variant={amtPercent >= 100 ? "filled" : "outlined"}
                        />
                    </Stack>
                    <LinearProgress 
                        variant="determinate" 
                        value={amtPercent} 
                        sx={{ height: 8, borderRadius: 4, mb: 1 }} 
                        color={execAmt > planAmt ? "error" : "primary"}
                    />
                    <Stack direction="row" justifyContent="space-between">
                        <Typography variant="caption">
                            Факт: <b>{formatMoney(execAmt)}</b>
                        </Typography>
                        <Typography variant="caption" color={remainingAmt < 0 ? "error.main" : "text.secondary"}>
                            Остаток: {formatMoney(remainingAmt)}
                        </Typography>
                    </Stack>
                </CardContent>
            </Card>
        </Stack>
    );
};

// --- Таблица истории ---
const ExecutionList = React.memo(({executions, onDelete, t}: {
    executions: Execution[],
    onDelete: (id: number) => void,
    t: (key: string) => string
}) => {
    return (
        <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <DescriptionIcon fontSize="small" color="action" />
                История исполнений
            </Typography>
            <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                    <TableHead sx={{ bgcolor: '#f5f5f5' }}>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 'bold' }}>{t('supplier')}</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>{t('contract_info')}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{t('quantity')}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{t('sum')}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{t('vc_mean_percent')}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{t('actions')}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {executions.map((exec) => (
                            <TableRow key={exec.id} hover>
                                <TableCell>
                                    <Typography variant="body2" fontWeight="500">{exec.supplier_name}</Typography>
                                    <Typography variant="caption" color="text.secondary">BIN: {exec.supplier_bin}</Typography>
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2">№{exec.contract_number}</Typography>
                                    <Typography variant="caption" color="text.secondary">{exec.contract_date}</Typography>
                                </TableCell>
                                <TableCell align="right">
                                    <Box>
                                        <Typography variant="body2">Дог: {formatNumber(exec.contract_quantity)}</Typography>
                                        <Typography variant="caption" color="success.main" fontWeight="bold">Факт: {formatNumber(exec.supply_volume_physical)}</Typography>
                                    </Box>
                                </TableCell>
                                <TableCell align="right">
                                    <Box>
                                        <Typography variant="body2">{formatMoney(exec.contract_sum)}</Typography>
                                        <Typography variant="caption" color="success.main" fontWeight="bold">{formatMoney(exec.supply_volume_value)}</Typography>
                                    </Box>
                                </TableCell>
                                <TableCell align="right">
                                    <Chip label={`${exec.fact_vc_percentage}%`} size="small" variant="outlined" />
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" color="error" onClick={() => onDelete(exec.id)}>
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                        {executions.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                                    {t('no_records')}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );
});

// --- Форма добавления ---
const ExecutionForm = React.memo(({
    itemId,
    planQuantity,
    planAmount,
    planPricePerUnit,
    executedQuantity,
    executedAmount,
    onSuccess,
    t,
    trucode,
    needType
}: {
    itemId: number,
    planQuantity: number,
    planAmount: number,
    planPricePerUnit: number,
    executedQuantity: number,
    executedAmount: number,
    onSuccess: () => void,
    t: (key: string) => string,
    trucode: string,
    needType: string
}) => {
    const [error, setError] = useState('');
    const [loadingSupplier, setLoadingSupplier] = useState(false);

    const contractNumberRef = useRef<HTMLInputElement>(null);
    const contractDateRef = useRef<HTMLInputElement>(null);
    
    const [contractQuantity, setContractQuantity] = useState<string>('');
    const [supplyPhysical, setSupplyPhysical] = useState<string>('');
    const [price, setPrice] = useState<string>('');
    const [supplierBin, setSupplierBin] = useState<string>('');
    const [supplierName, setSupplierName] = useState<string>('');
    const [factVcPercentage, setFactVcPercentage] = useState<string>('0');
    
    const [foundSuppliers, setFoundSuppliers] = useState<KtpSupplier[]>([]);
    const [selectedCertificate, setSelectedCertificate] = useState<KtpSupplier | null>(null);
    const [isSupplierFromDB, setIsSupplierFromDB] = useState(false);

    const remainingPlanQuantity = planQuantity - executedQuantity;
    const remainingPlanAmount = planAmount - executedAmount;

    const currentContractQuantity = Number(contractQuantity) || 0;
    const currentSupplyPhysical = Number(supplyPhysical) || 0;
    const currentPrice = Number(price) || 0;
    
    const currentContractSum = currentContractQuantity * currentPrice;
    const currentSupplyValue = currentSupplyPhysical * currentPrice;
    const currentVcPercentage = Number(factVcPercentage) || 0;

    const validation = useMemo(() => ({
        isContractQuantityOverLimit: currentContractQuantity > remainingPlanQuantity + 0.001,
        isContractAmountOverLimit: currentContractSum > remainingPlanAmount + 0.01,
        isPriceOverLimit: currentPrice > planPricePerUnit + 0.01,
        isSupplyOverContract: currentSupplyPhysical > currentContractQuantity + 0.001,
        isBinInvalid: supplierBin.length > 0 && supplierBin.length !== 12,
        isVcPercentageInvalid: currentVcPercentage < 0 || currentVcPercentage > 100
    }), [currentContractQuantity, currentSupplyPhysical, currentPrice, currentContractSum, remainingPlanQuantity, remainingPlanAmount, planPricePerUnit, supplierBin, currentVcPercentage]);

    const handleBinChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        if (/^\d*$/.test(val) && val.length <= 12) {
            setSupplierBin(val);
            
            setSupplierName('');
            setFoundSuppliers([]);
            setSelectedCertificate(null);
            setFactVcPercentage('0');
            setIsSupplierFromDB(false);

            if (val.length === 12) {
                setLoadingSupplier(true);
                try {
                    const suppliers = await getSupplierByBin(val, trucode);
                    setFoundSuppliers(suppliers);
                    
                    if (suppliers.length > 0) {
                        setSupplierName(suppliers[0].company_name);
                        setIsSupplierFromDB(true);
                        if (suppliers.length === 1) {
                            const supplier = suppliers[0];
                            setSelectedCertificate(supplier);
                            setFactVcPercentage(String(supplier.dvc_percent || 0));
                        }
                    }
                } catch (err) {
                    console.error(err);
                } finally {
                    setLoadingSupplier(false);
                }
            }
        }
    };
    
    const handleCertificateSelect = (event: any, newValue: KtpSupplier | null) => {
        setSelectedCertificate(newValue);
        setFactVcPercentage(newValue?.dvc_percent ? String(newValue.dvc_percent) : '0');
    };

    const handleSubmit = async () => {
        const contractNumber = contractNumberRef.current?.value;
        const contractDate = contractDateRef.current?.value;

        if (!supplierName || !supplierBin || !contractNumber || !contractDate) {
            setError(t('fill_required_fields'));
            return;
        }
        if (supplierBin.length !== 12) { setError(t('error_bin_length')); return; }
        if (validation.isContractQuantityOverLimit) { setError(`Кол-во по договору превышает остаток плана (${formatNumber(remainingPlanQuantity)})`); return; }
        if (validation.isContractAmountOverLimit) { setError(`Сумма по договору превышает остаток плана (${formatMoney(remainingPlanAmount)})`); return; }
        if (validation.isPriceOverLimit) { setError(`${t('error_price_exceeds_plan')} (${planPricePerUnit})`); return; }
        if (validation.isSupplyOverContract) { setError("Объем поставки не может превышать количество по договору"); return; }
        if (validation.isVcPercentageInvalid) { setError("Процент ВЦ должен быть от 0 до 100"); return; }
        if (foundSuppliers.length > 1 && !selectedCertificate) {
             setError("Выберите товар из реестра КТП");
             return;
        }

        try {
            const payload: ExecutionPayload = {
                plan_item_id: itemId,
                supplier_name: supplierName,
                supplier_bin: supplierBin,
                contract_number: contractNumber,
                contract_date: contractDate,
                contract_quantity: currentContractQuantity,
                contract_price_per_unit: currentPrice,
                fact_vc_percentage: Number(factVcPercentage),
                supply_volume_physical: currentSupplyPhysical,
                supply_volume_value: currentSupplyValue,
            };

            await createExecution(payload);
            
            setSupplierName(''); setSupplierBin(''); setFoundSuppliers([]); setSelectedCertificate(null);
            setFactVcPercentage('0'); setIsSupplierFromDB(false);
            if (contractNumberRef.current) contractNumberRef.current.value = '';
            if (contractDateRef.current) contractDateRef.current.value = '';
            setContractQuantity(''); setSupplyPhysical(''); setPrice('');
            setError('');
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || t('error_saving_execution'));
        }
    };
    
    const hasValidCertificate = selectedCertificate && selectedCertificate.dvc_percent && selectedCertificate.dvc_percent > 0;
    let isVcDisabled = false;
    let vcHelperText = "";

    if (hasValidCertificate) {
        isVcDisabled = true;
        vcHelperText = "Значение из реестра КТП";
    } else if (needType === 'GOODS') {
        isVcDisabled = true;
        vcHelperText = "Для товаров без сертификата КТП ВЦ = 0%";
    } else {
        isVcDisabled = false;
        vcHelperText = "Укажите процент вручную";
    }

    return (
        <Paper elevation={0} variant="outlined" sx={{ p: 3, mb: 4, bgcolor: '#fff' }}>
            <Typography variant="h6" gutterBottom sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AddIcon color="primary" /> {t('add_new_record')}
            </Typography>
            
            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            <Stack spacing={2.5}>
                {/* --- Секция 1: Поставщик --- */}
                <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BusinessIcon fontSize="small" /> Данные поставщика
                    </Typography>
                    <Divider sx={{ mb: 2, mt: 1 }} />
                    <Stack spacing={2}>
                        <TextField
                            fullWidth
                            label={t('supplier_bin')}
                            value={supplierBin}
                            onChange={handleBinChange}
                            required
                            error={validation.isBinInvalid}
                            helperText={validation.isBinInvalid ? "12 цифр" : ""}
                            inputProps={{ maxLength: 12 }}
                            InputProps={{
                                endAdornment: loadingSupplier ? <CircularProgress size={20} /> : <InputAdornment position="end"><SearchIcon color="action" /></InputAdornment>
                            }}
                            size="small"
                        />
                        <TextField
                            fullWidth
                            label={t('supplier_name')}
                            value={supplierName}
                            onChange={(e) => setSupplierName(e.target.value)}
                            required
                            disabled={isSupplierFromDB}
                            size="small"
                            sx={{ bgcolor: isSupplierFromDB ? '#f5f5f5' : 'inherit' }}
                        />
                    </Stack>
                </Box>

                {/* --- Секция 2: Договор --- */}
                <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ContractIcon fontSize="small" /> Договор
                    </Typography>
                    <Divider sx={{ mb: 2, mt: 1 }} />
                    <Stack spacing={2}>
                        <TextField
                            fullWidth
                            label={t('contract_number')}
                            inputRef={contractNumberRef}
                            required
                            size="small"
                            InputProps={{ startAdornment: <InputAdornment position="start"><NumberIcon fontSize="small" /></InputAdornment> }}
                        />
                        <TextField
                            fullWidth
                            type="date"
                            label={t('contract_date')}
                            inputRef={contractDateRef}
                            InputLabelProps={{ shrink: true }}
                            required
                            size="small"
                        />
                        <TextField
                            fullWidth
                            type="number"
                            label="Кол-во по договору"
                            value={contractQuantity}
                            onChange={(e) => setContractQuantity(e.target.value)}
                            required
                            error={validation.isContractQuantityOverLimit}
                            helperText={validation.isContractQuantityOverLimit ? `Превышен остаток плана (${formatNumber(remainingPlanQuantity)})` : ""}
                            size="small"
                            onWheel={(e) => (e.target as HTMLElement).blur()}
                        />
                        <TextField
                            fullWidth
                            type="number"
                            label={t('contract_price')}
                            value={price}
                            onChange={(e) => setPrice(e.target.value)}
                            required
                            error={validation.isPriceOverLimit}
                            helperText={validation.isPriceOverLimit ? `${t('max_price')}: ${planPricePerUnit}` : ''}
                            size="small"
                            InputProps={{ endAdornment: <InputAdornment position="end">₸</InputAdornment> }}
                            onWheel={(e) => (e.target as HTMLElement).blur()}
                        />
                        <TextField
                            fullWidth
                            type="number"
                            label="Сумма договора"
                            value={currentContractSum.toFixed(2)}
                            disabled
                            error={validation.isContractAmountOverLimit}
                            helperText={validation.isContractAmountOverLimit ? `Превышен остаток плана (${formatMoney(remainingPlanAmount)})` : ""}
                            size="small"
                            sx={{ bgcolor: '#f9f9f9' }}
                            InputProps={{ endAdornment: <InputAdornment position="end">₸</InputAdornment> }}
                        />
                    </Stack>
                </Box>

                {/* --- Секция 3: Факт поставки --- */}
                <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SupplyIcon fontSize="small" /> Факт поставки (Акт)
                    </Typography>
                    <Divider sx={{ mb: 2, mt: 1 }} />
                    <Stack spacing={2}>
                        <TextField
                            fullWidth
                            type="number"
                            label="Объем поставки (нат.)"
                            value={supplyPhysical}
                            onChange={(e) => setSupplyPhysical(e.target.value)}
                            required
                            error={validation.isSupplyOverContract}
                            helperText={validation.isSupplyOverContract ? "Не может быть больше кол-ва по договору" : ""}
                            size="small"
                            onWheel={(e) => (e.target as HTMLElement).blur()}
                        />
                        <TextField
                            fullWidth
                            type="number"
                            label="Объем поставки (стоим.)"
                            value={currentSupplyValue.toFixed(2)}
                            disabled
                            size="small"
                            sx={{ bgcolor: '#e8f5e9' }}
                            InputProps={{ endAdornment: <InputAdornment position="end">₸</InputAdornment> }}
                        />
                    </Stack>
                </Box>

                {/* --- Секция 4: Местное содержание --- */}
                <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PercentIcon fontSize="small" /> Внутристрановая ценность
                    </Typography>
                    <Divider sx={{ mb: 2, mt: 1 }} />
                    <Stack spacing={2}>
                        {foundSuppliers.length > 1 && (
                            <Autocomplete
                                fullWidth
                                options={foundSuppliers}
                                getOptionLabel={(option) => `${option.product_name} (ВЦ: ${option.dvc_percent}%)`}
                                value={selectedCertificate}
                                onChange={handleCertificateSelect}
                                renderInput={(params) => (
                                    <TextField {...params} label="Выберите товар из реестра КТП" size="small" />
                                )}
                                renderOption={(props, option) => (
                                    <li {...props} key={option.id}>
                                        <Box>
                                            <Typography variant="body2" fontWeight="bold">{option.product_name}</Typography>
                                            <Typography variant="caption" display="block">ВЦ: {option.dvc_percent}% | {option.production_address}</Typography>
                                        </Box>
                                    </li>
                                )}
                            />
                        )}
                        <TextField
                            fullWidth
                            type="number"
                            label={t('vc_mean_percent')}
                            value={factVcPercentage}
                            onChange={(e) => setFactVcPercentage(e.target.value)}
                            required
                            disabled={isVcDisabled}
                            helperText={vcHelperText}
                            size="small"
                            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                            sx={{ bgcolor: isVcDisabled ? '#f5f5f5' : 'inherit' }}
                            onWheel={(e) => (e.target as HTMLElement).blur()}
                        />
                    </Stack>
                </Box>
            </Stack>
            
            <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleSubmit}
                    disabled={validation.isContractQuantityOverLimit || validation.isContractAmountOverLimit || validation.isPriceOverLimit || validation.isBinInvalid || !supplierBin || validation.isVcPercentageInvalid || validation.isSupplyOverContract}
                    size="large"
                    sx={{ px: 4 }}
                >
                    {t('add_record')}
                </Button>
            </Box>
        </Paper>
    );
});

const ExecutionModal: React.FC<ExecutionModalProps> = ({
                                                           open,
                                                           onClose,
                                                           itemId,
                                                           itemName,
                                                           planQuantity,
                                                           planAmount,
                                                           planPricePerUnit,
                                                           trucode,
                                                           needType
                                                       }) => {
    const {t} = useTranslation();
    const [executions, setExecutions] = useState<Execution[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (open && itemId) {
            loadExecutions();
            setError('');
        }
    }, [open, itemId]);

    const loadExecutions = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getExecutionsByItem(itemId);
            setExecutions(data);
        } catch (err) {
            console.error(err);
            setError(t('error_loading_executions'));
        } finally {
            setLoading(false);
        }
    }, [itemId, t]);

    const handleDelete = useCallback(async (id: number) => {
        if (window.confirm(t('confirm_delete_execution'))) {
            try {
                await deleteExecution(id);
                loadExecutions();
            } catch (err) {
                setError(t('error_deleting_execution'));
            }
        }
    }, [t, loadExecutions]);

    const { executedQuantity, executedAmount } = useMemo(() => {
        return executions.reduce((acc, exec) => ({
            executedQuantity: acc.executedQuantity + Number(exec.supply_volume_physical),
            executedAmount: acc.executedAmount + Number(exec.supply_volume_value)
        }), { executedQuantity: 0, executedAmount: 0 });
    }, [executions]);

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle sx={{ pb: 1, borderBottom: '1px solid #eee' }}>
                <Typography variant="h6" component="div">{t('execution_report_title')}</Typography>
                <Typography variant="body2" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
                    {itemName}
                </Typography>
            </DialogTitle>
            
            <DialogContent sx={{ p: 3, bgcolor: '#fafafa' }}>
                {error && <Alert severity="error" sx={{mb: 2}}>{error}</Alert>}

                <ExecutionSummary 
                    planQty={planQuantity} 
                    planAmt={planAmount} 
                    execQty={executedQuantity}
                    execAmt={executedAmount} 
                    t={t} 
                />

                <ExecutionForm
                    itemId={itemId}
                    planQuantity={planQuantity}
                    planAmount={planAmount}
                    planPricePerUnit={planPricePerUnit}
                    executedQuantity={executedQuantity}
                    executedAmount={executedAmount}
                    onSuccess={loadExecutions}
                    t={t}
                    trucode={trucode}
                    needType={needType}
                />

                <ExecutionList
                    executions={executions}
                    onDelete={handleDelete}
                    t={t}
                />
            </DialogContent>
            <DialogActions sx={{ p: 2, borderTop: '1px solid #eee', bgcolor: '#fff' }}>
                <Button onClick={onClose} variant="outlined">{t('close')}</Button>
            </DialogActions>
        </Dialog>
    );
};

export default ExecutionModal;
