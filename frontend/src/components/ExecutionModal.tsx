import React, {useState, useEffect, useMemo, useCallback, useRef} from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    TextField, Typography, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, IconButton, Box, Alert, LinearProgress, Stack
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {Delete as DeleteIcon, Add as AddIcon} from '@mui/icons-material';
import {useTranslation} from '../i18n/index.tsx';
import {createExecution, getExecutionsByItem, deleteExecution} from '../services/api';
import type {Execution, ExecutionPayload} from '../services/api';

interface ExecutionModalProps {
    open: boolean;
    onClose: () => void;
    itemId: number;
    itemName: string;
    planQuantity: number;
    planAmount: number;
    planPricePerUnit: number;
}

const formatMoney = (val: number) => new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'KZT'}).format(val);

// Таблица вынесена и мемоизирована
const ExecutionList = React.memo(({executions, onDelete, t}: {
    executions: Execution[],
    onDelete: (id: number) => void,
    t: (key: string) => string
}) => {
    return (
        <TableContainer component={Paper}>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>{t('supplier')}</TableCell>
                        <TableCell>{t('contract_info')}</TableCell>
                        <TableCell align="right">{t('quantity')}</TableCell>
                        <TableCell align="right">{t('sum')}</TableCell>
                        <TableCell align="right">{t('actions')}</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {executions.map((exec) => (
                        <TableRow key={exec.id}>
                            <TableCell>
                                <Typography variant="body2">{exec.supplier_name}</Typography>
                                <Typography variant="caption"
                                            color="text.secondary">BIN: {exec.supplier_bin}</Typography>
                            </TableCell>
                            <TableCell>
                                <Typography variant="body2">№{exec.contract_number}</Typography>
                                <Typography variant="caption" color="text.secondary">{exec.contract_date}</Typography>
                            </TableCell>
                            <TableCell align="right">{exec.contract_quantity}</TableCell>
                            <TableCell align="right">{formatMoney(exec.contract_sum)}</TableCell>
                            <TableCell align="right">
                                <IconButton size="small" color="error" onClick={() => onDelete(exec.id)}>
                                    <DeleteIcon/>
                                </IconButton>
                            </TableCell>
                        </TableRow>
                    ))}
                    {executions.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={5} align="center">{t('no_records')}</TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    );
});

// Форма с гибридным подходом: useState для важных полей, useRef для остальных
// Форма с гибридным подходом: useState для важных полей, useRef для остальных
const ExecutionForm = React.memo(({
    itemId,
    planQuantity,
    planAmount,
    planPricePerUnit,
    contractedQuantity,
    contractedAmount,
    onSuccess,
    t
}: {
    itemId: number,
    planQuantity: number,
    planAmount: number,
    planPricePerUnit: number,
    contractedQuantity: number,
    contractedAmount: number,
    onSuccess: () => void,
    t: (key: string) => string
}) => {
    const [error, setError] = useState('');

    // Refs для текстовых полей
    const supplierNameRef = useRef<HTMLInputElement>(null);
    const residencyCodeRef = useRef<HTMLInputElement>(null);
    const originCodeRef = useRef<HTMLInputElement>(null);
    const contractNumberRef = useRef<HTMLInputElement>(null);
    const contractDateRef = useRef<HTMLInputElement>(null);
    const supplyPhysicalRef = useRef<HTMLInputElement>(null);
    const supplyValueRef = useRef<HTMLInputElement>(null);

    // State для полей с валидацией
    const [quantity, setQuantity] = useState<string>('');
    const [price, setPrice] = useState<string>('');
    const [supplierBin, setSupplierBin] = useState<string>('');

    const remainingQuantity = planQuantity - contractedQuantity;
    const remainingAmount = planAmount - contractedAmount;

    const currentQuantity = Number(quantity) || 0;
    const currentPrice = Number(price) || 0;
    const currentSum = currentQuantity * currentPrice;

    // Мгновенная валидация
    const validation = useMemo(() => ({
        isQuantityOverLimit: currentQuantity > remainingQuantity + 0.001,
        isPriceOverLimit: currentPrice > planPricePerUnit + 0.01,
        isAmountOverLimit: currentSum > remainingAmount + 0.01,
        isBinInvalid: supplierBin.length > 0 && supplierBin.length !== 12
    }), [currentQuantity, currentPrice, currentSum, remainingQuantity, remainingAmount, planPricePerUnit, supplierBin]);

    const handleBinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        // Принимаем только цифры и максимум 12 символов
        if (/^\d*$/.test(val) && val.length <= 12) {
            setSupplierBin(val);
        }
    };

    const handleSubmit = async () => {
        const supplierName = supplierNameRef.current?.value;
        const contractNumber = contractNumberRef.current?.value;
        const contractDate = contractDateRef.current?.value;

        if (!supplierName || !supplierBin || !contractNumber || !contractDate) {
            setError(t('fill_required_fields'));
            return;
        }

        if (supplierBin.length !== 12) {
            setError(t('error_bin_length'));
            return;
        }

        if (validation.isQuantityOverLimit) {
            setError(t('error_quantity_exceeds_plan'));
            return;
        }

        if (validation.isPriceOverLimit) {
            setError(`${t('error_price_exceeds_plan')} (${planPricePerUnit})`);
            return;
        }

        if (validation.isAmountOverLimit) {
            setError(t('error_amount_exceeds_plan'));
            return;
        }

        try {
            const payload: ExecutionPayload = {
                plan_item_id: itemId,
                supplier_name: supplierName,
                supplier_bin: supplierBin,
                residency_code: residencyCodeRef.current?.value || '',
                origin_code: originCodeRef.current?.value || '',
                contract_number: contractNumber,
                contract_date: contractDate,
                contract_quantity: currentQuantity,
                contract_price_per_unit: currentPrice,
                supply_volume_physical: Number(supplyPhysicalRef.current?.value || 0),
                supply_volume_value: Number(supplyValueRef.current?.value || 0),
            };

            await createExecution(payload);

            // Очистка полей
            if (supplierNameRef.current) supplierNameRef.current.value = '';
            if (residencyCodeRef.current) residencyCodeRef.current.value = '';
            if (originCodeRef.current) originCodeRef.current.value = '';
            if (contractNumberRef.current) contractNumberRef.current.value = '';
            if (contractDateRef.current) contractDateRef.current.value = '';
            if (supplyPhysicalRef.current) supplyPhysicalRef.current.value = '';
            if (supplyValueRef.current) supplyValueRef.current.value = '';
            setQuantity('');
            setPrice('');
            setSupplierBin('');

            setError('');
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || t('error_saving_execution'));
        }
    };

    return (
        <Box sx={{
            mb: 4,
            p: 2,
            border: '1px solid #eee',
            borderRadius: 1,
            width: '100%',
            boxSizing: 'border-box'
        }}>
            <Typography variant="h6" gutterBottom>{t('add_new_record')}</Typography>
            {error && <Alert severity="error" sx={{ mb: 2, width: '100%' }}>{error}</Alert>}

            {/* Все поля расположены в строках как на скриншоте */}

            {/* 1. Supplier Name (полная ширина) */}
            <TextField
                fullWidth
                label={t('supplier_name')}
                inputRef={supplierNameRef}
                required
                size="medium"
                sx={{ mb: 2 }}
            />

            {/* 2. Supplier BIN (полная ширина) */}
            <TextField
                fullWidth
                label={t('supplier_bin')}
                value={supplierBin}
                onChange={handleBinChange}
                required
                error={validation.isBinInvalid}
                helperText={validation.isBinInvalid ? "БИН должен состоять из 12 цифр" : ""}
                inputProps={{ maxLength: 12 }}
                sx={{ mb: 2 }}
            />

            {/* 3. Residency Code и Origin Code в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                    fullWidth
                    label={t('residency_code')}
                    inputRef={residencyCodeRef}
                    required
                    sx={{ flex: 1 }}
                />
                <TextField
                    fullWidth
                    label={t('origin_code')}
                    inputRef={originCodeRef}
                    required
                    sx={{ flex: 1 }}
                />
            </Box>

            {/* 4. Contract Number и Contract Date в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                    fullWidth
                    label={t('contract_number')}
                    inputRef={contractNumberRef}
                    required
                    sx={{ flex: 1 }}
                />
                <TextField
                    fullWidth
                    type="date"
                    label={t('contract_date')}
                    inputRef={contractDateRef}
                    InputLabelProps={{ shrink: true }}
                    required
                    sx={{ flex: 1 }}
                />
            </Box>

            {/* 5. Quantity, Price, Sum в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                    fullWidth
                    type="number"
                    label={t('contract_quantity')}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    required
                    error={validation.isQuantityOverLimit}
                    helperText={validation.isQuantityOverLimit ? t('error_quantity_exceeds_plan') : ''}
                    sx={{ flex: 1 }}
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
                    sx={{ flex: 1 }}
                />
                <TextField
                    fullWidth
                    type="number"
                    label={t('contract_sum')}
                    value={currentSum.toFixed(2)}
                    disabled
                    error={validation.isAmountOverLimit}
                    helperText={validation.isAmountOverLimit ? t('error_amount_exceeds_plan') : ''}
                    sx={{ flex: 1 }}
                />
            </Box>

            {/* 6. Supply Volume Physical и Value в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <TextField
                    fullWidth
                    type="number"
                    label={t('supply_volume_physical')}
                    inputRef={supplyPhysicalRef}
                    required
                    sx={{ flex: 1 }}
                />
                <TextField
                    fullWidth
                    type="number"
                    label={t('supply_volume_value')}
                    inputRef={supplyValueRef}
                    required
                    sx={{ flex: 1 }}
                />
            </Box>

            {/* Кнопка добавления */}
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleSubmit}
                    disabled={validation.isQuantityOverLimit || validation.isPriceOverLimit || validation.isAmountOverLimit || validation.isBinInvalid || !supplierBin}
                    sx={{ minWidth: 200 }}
                >
                    {t('add_record')}
                </Button>
            </Box>
        </Box>
    );
});

const ExecutionModal: React.FC<ExecutionModalProps> = ({
                                                           open,
                                                           onClose,
                                                           itemId,
                                                           itemName,
                                                           planQuantity,
                                                           planAmount,
                                                           planPricePerUnit
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

    const {contractedQuantity, contractedAmount} = useMemo(() => {
        return executions.reduce((acc, exec) => ({
            contractedQuantity: acc.contractedQuantity + Number(exec.contract_quantity),
            contractedAmount: acc.contractedAmount + Number(exec.contract_sum)
        }), {contractedQuantity: 0, contractedAmount: 0});
    }, [executions]);

    const remainingQuantity = planQuantity - contractedQuantity;
    const remainingAmount = planAmount - contractedAmount;

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
        >
            <DialogTitle sx={{pb: 2}}>
                <Typography variant="h6">{t('execution_report_title')}</Typography>
                <Typography variant="subtitle2" color="text.secondary">{itemName}</Typography>
            </DialogTitle>
            <DialogContent dividers sx={{p: 3}}>
                {error && <Alert severity="error" sx={{mb: 2, width: '100%'}}>{error}</Alert>}

                {/* Progress Bars - увеличенные и на всю ширину 50/50 */}
                <Box sx={{
    mb: 4,
    p: 3,
    bgcolor: '#f9f9f9',
    borderRadius: 1,
    width: '100%',
    boxSizing: 'border-box'
}}>
    {/* Прогресс-бары в одной строке */}
    <Box sx={{ display: 'flex', gap: 3, width: '100%' }}>
        {/* Прогресс по количеству */}
        <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">{t('quantity_progress')}</Typography>
            <Stack direction="row" justifyContent="space-between" mb={1}>
                <Typography variant="body2">{t('plan')}: {planQuantity}</Typography>
                <Typography variant="body2" color={remainingQuantity < 0 ? 'error.main' : 'success.main'} fontWeight="bold">
                    {t('remaining')}: {remainingQuantity.toFixed(2)}
                </Typography>
            </Stack>
            <LinearProgress
                variant="determinate"
                value={Math.min((contractedQuantity / planQuantity) * 100, 100)}
                color={contractedQuantity > planQuantity ? 'error' : 'primary'}
                sx={{ height: 16, borderRadius: 8 }}
            />
        </Box>

        {/* Прогресс по сумме */}
        <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">{t('amount_progress')}</Typography>
            <Stack direction="row" justifyContent="space-between" mb={1}>
                <Typography variant="body2">{t('plan')}: {formatMoney(planAmount)}</Typography>
                <Typography variant="body2" color={remainingAmount < 0 ? 'error.main' : 'success.main'} fontWeight="bold">
                    {t('remaining')}: {formatMoney(remainingAmount)}
                </Typography>
            </Stack>
            <LinearProgress
                variant="determinate"
                value={Math.min((contractedAmount / planAmount) * 100, 100)}
                color={contractedAmount > planAmount ? 'error' : 'primary'}
                sx={{ height: 16, borderRadius: 8 }}
            />
        </Box>
    </Box>
</Box>

                <ExecutionForm
                    itemId={itemId}
                    planQuantity={planQuantity}
                    planAmount={planAmount}
                    planPricePerUnit={planPricePerUnit}
                    contractedQuantity={contractedQuantity}
                    contractedAmount={contractedAmount}
                    onSuccess={loadExecutions}
                    t={t}
                />

                <ExecutionList
                    executions={executions}
                    onDelete={handleDelete}
                    t={t}
                />
            </DialogContent>
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose}>{t('close')}</Button>
            </DialogActions>
        </Dialog>
    );
};

export default ExecutionModal;