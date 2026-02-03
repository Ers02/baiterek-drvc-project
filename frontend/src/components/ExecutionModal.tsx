import React, {useState, useEffect, useMemo, useCallback, useRef} from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    TextField, Typography, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, IconButton, Box, Alert, LinearProgress, Stack, CircularProgress, Autocomplete, Link
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {Delete as DeleteIcon, Add as AddIcon, Edit as EditIcon, Refresh as RefreshIcon} from '@mui/icons-material';
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
                        <TableCell align="right">{t('vc_mean_percent')}</TableCell>
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
                            <TableCell align="right">
                                <Box>
                                    <Typography variant="body2">Договор: {exec.contract_quantity}</Typography>
                                    <Typography variant="caption" color="success.main">Факт: {exec.supply_volume_physical}</Typography>
                                </Box>
                            </TableCell>
                            <TableCell align="right">
                                <Box>
                                    <Typography variant="body2">{formatMoney(exec.contract_sum)}</Typography>
                                    <Typography variant="caption" color="success.main">{formatMoney(exec.supply_volume_value)}</Typography>
                                </Box>
                            </TableCell>
                            <TableCell align="right">{exec.fact_vc_percentage}%</TableCell>
                            <TableCell align="right">
                                <IconButton size="small" color="error" onClick={() => onDelete(exec.id)}>
                                    <DeleteIcon/>
                                </IconButton>
                            </TableCell>
                        </TableRow>
                    ))}
                    {executions.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={6} align="center">{t('no_records')}</TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    );
});

// Форма с гибридным подходом: useState для важных полей, useRef для остальных
const ExecutionForm = React.memo(({
    itemId,
    planQuantity,
    planAmount,
    planPricePerUnit,
    executedQuantity, // Используем executedQuantity вместо contractedQuantity
    executedAmount,   // Используем executedAmount вместо contractedAmount
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

    // Refs для текстовых полей
    const contractNumberRef = useRef<HTMLInputElement>(null);
    const contractDateRef = useRef<HTMLInputElement>(null);
    
    // State для полей с валидацией
    const [contractQuantity, setContractQuantity] = useState<string>('');
    const [supplyPhysical, setSupplyPhysical] = useState<string>('');
    const [price, setPrice] = useState<string>('');
    const [supplierBin, setSupplierBin] = useState<string>('');
    const [supplierName, setSupplierName] = useState<string>('');
    const [factVcPercentage, setFactVcPercentage] = useState<string>('0');
    
    // State for KTP Suppliers found
    const [foundSuppliers, setFoundSuppliers] = useState<KtpSupplier[]>([]);
    const [selectedCertificate, setSelectedCertificate] = useState<KtpSupplier | null>(null);
    
    // Режим ручного ввода (когда поставщик найден, но пользователь хочет ввести другое)
    const [isManualMode, setIsManualMode] = useState(false);

    // Остаток считаем от ФАКТА
    const remainingQuantity = planQuantity - executedQuantity;
    const remainingAmount = planAmount - executedAmount;

    const currentContractQuantity = Number(contractQuantity) || 0;
    const currentSupplyPhysical = Number(supplyPhysical) || 0;
    const currentPrice = Number(price) || 0;
    
    const currentContractSum = currentContractQuantity * currentPrice;
    const currentSupplyValue = currentSupplyPhysical * currentPrice;
    
    const currentVcPercentage = Number(factVcPercentage) || 0;

    // Мгновенная валидация
    const validation = useMemo(() => ({
        // Проверяем объем поставки против остатка плана (по факту)
        // ВАЖНО: Мы проверяем именно ФАКТ поставки (currentSupplyPhysical), так как остаток считается от факта.
        // Если проверять currentContractQuantity, то мы можем превысить план, если договор большой, а поставка маленькая.
        // Но пользователь просил "исправь логику чтобы по плану высчитывало то что поставлено по факту".
        // Значит, лимитирующим фактором является ФАКТ.
        
        // Однако, если мы вводим новый договор, то его объем тоже важен.
        // Если мы разрешаем contractQuantity > remainingQuantity, то это овербукинг.
        // Давайте проверим supplyPhysical > remainingQuantity.
        
        isQuantityOverLimit: currentSupplyPhysical > remainingQuantity + 0.001,
        isPriceOverLimit: currentPrice > planPricePerUnit + 0.01,
        isAmountOverLimit: currentSupplyValue > remainingAmount + 0.01,
        
        // Объем поставки не может быть больше объема договора
        isSupplyOverContract: currentSupplyPhysical > currentContractQuantity + 0.001,
        
        isBinInvalid: supplierBin.length > 0 && supplierBin.length !== 12,
        isVcPercentageInvalid: currentVcPercentage < 0 || currentVcPercentage > 100
    }), [currentContractQuantity, currentSupplyPhysical, currentPrice, currentSupplyValue, remainingQuantity, remainingAmount, planPricePerUnit, supplierBin, currentVcPercentage]);

    const handleBinChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        // Принимаем только цифры и максимум 12 символов
        if (/^\d*$/.test(val) && val.length <= 12) {
            setSupplierBin(val);
            
            if (val.length === 12) {
                setLoadingSupplier(true);
                setIsManualMode(false); // Сбрасываем ручной режим при новом поиске
                try {
                    const suppliers = await getSupplierByBin(val, trucode);
                    setFoundSuppliers(suppliers);
                    
                    if (suppliers.length > 0) {
                        // Берем имя из первого найденного (оно должно быть одинаковым)
                        setSupplierName(suppliers[0].company_name);
                        
                        if (suppliers.length === 1) {
                            // Если только один сертификат, выбираем его сразу
                            const supplier = suppliers[0];
                            setSelectedCertificate(supplier);
                            if (supplier.dvc_percent && supplier.dvc_percent > 0) {
                                setFactVcPercentage(String(supplier.dvc_percent));
                            } else {
                                setFactVcPercentage('0');
                            }
                        } else {
                            // Если несколько, сбрасываем выбор, чтобы пользователь выбрал сам
                            setSelectedCertificate(null);
                            setFactVcPercentage('0');
                        }
                    } else {
                        // Поставщик не найден
                        setSupplierName(''); 
                        setSelectedCertificate(null);
                        setFactVcPercentage('0');
                    }
                } catch (err) {
                    console.error("Error fetching supplier:", err);
                } finally {
                    setLoadingSupplier(false);
                }
            } else {
                // Если БИН не полный, сбрасываем данные
                if (foundSuppliers.length > 0) {
                    setSupplierName('');
                    setFoundSuppliers([]);
                    setSelectedCertificate(null);
                    setFactVcPercentage('0');
                    setIsManualMode(false);
                }
            }
        }
    };
    
    const handleCertificateSelect = (event: any, newValue: KtpSupplier | null) => {
        setSelectedCertificate(newValue);
        if (newValue && newValue.dvc_percent && newValue.dvc_percent > 0) {
            setFactVcPercentage(String(newValue.dvc_percent));
        } else {
            setFactVcPercentage('0');
        }
    };
    
    const toggleManualMode = () => {
        const newMode = !isManualMode;
        setIsManualMode(newMode);
        
        if (newMode) {
            // Включаем ручной режим
            setSelectedCertificate(null);
            setFactVcPercentage('0');
            // Имя оставляем, чтобы пользователь мог его отредактировать, если нужно
        } else {
            // Выключаем ручной режим (возвращаемся к найденному)
            if (foundSuppliers.length > 0) {
                setSupplierName(foundSuppliers[0].company_name);
                if (foundSuppliers.length === 1) {
                    const supplier = foundSuppliers[0];
                    setSelectedCertificate(supplier);
                    setFactVcPercentage(String(supplier.dvc_percent || 0));
                } else {
                    setSelectedCertificate(null);
                    setFactVcPercentage('0');
                }
            }
        }
    };

    const handleSubmit = async () => {
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
        
        if (validation.isSupplyOverContract) {
            setError("Объем поставки не может превышать количество по договору");
            return;
        }
        
        if (validation.isVcPercentageInvalid) {
            setError("Процент ВЦ должен быть от 0 до 100");
            return;
        }
        
        // Если найдено несколько сертификатов, но ни один не выбран, И мы не в ручном режиме
        if (foundSuppliers.length > 1 && !selectedCertificate && !isManualMode) {
             setError("Выберите товар из списка сертификатов поставщика или переключитесь в ручной режим");
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

            // Очистка полей
            setSupplierName('');
            setSupplierBin('');
            setFoundSuppliers([]);
            setSelectedCertificate(null);
            setFactVcPercentage('0');
            setIsManualMode(false);
            if (contractNumberRef.current) contractNumberRef.current.value = '';
            if (contractDateRef.current) contractDateRef.current.value = '';
            setContractQuantity('');
            setSupplyPhysical('');
            setPrice('');

            setError('');
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || t('error_saving_execution'));
        }
    };
    
    // Логика блокировки поля ВЦ
    const hasValidCertificate = selectedCertificate && selectedCertificate.dvc_percent && selectedCertificate.dvc_percent > 0;
    
    // Блокируем если:
    // 1. Выбран валидный сертификат (не в ручном режиме).
    // 2. Это ТОВАР и (нет сертификата ИЛИ ручной режим) -> ВЦ = 0 и заблокировано.
    // Для РАБОТ/УСЛУГ в ручном режиме поле активно.
    
    let isVcDisabled = false;
    let vcHelperText = "";

    if (!isManualMode && hasValidCertificate) {
        isVcDisabled = true;
        vcHelperText = "Используется значение из сертификата";
    } else if (needType === 'GOODS') {
        isVcDisabled = true;
        vcHelperText = "Для товаров без сертификата КТП ВЦ = 0%";
    } else {
        // Ручной режим или нет сертификата, но это Работа/Услуга
        isVcDisabled = false;
        vcHelperText = "Укажите процент ВЦ вручную";
    }

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

            {/* 1. Supplier BIN (полная ширина) */}
            <TextField
                fullWidth
                label={t('supplier_bin')}
                value={supplierBin}
                onChange={handleBinChange}
                required
                error={validation.isBinInvalid}
                helperText={validation.isBinInvalid ? "БИН должен состоять из 12 цифр" : ""}
                inputProps={{ maxLength: 12 }}
                InputProps={{
                    endAdornment: loadingSupplier ? <CircularProgress size={20} /> : null
                }}
                sx={{ mb: 2 }}
            />

            {/* 2. Supplier Name */}
            <Box sx={{ mb: 2 }}>
                <TextField
                    fullWidth
                    label={t('supplier_name')}
                    value={supplierName}
                    onChange={(e) => setSupplierName(e.target.value)}
                    required
                    disabled={foundSuppliers.length > 0 && !isManualMode} // Блокируем, если нашли в базе и не ручной режим
                    helperText={
                        foundSuppliers.length > 0 
                        ? (isManualMode ? "Ручной ввод наименования" : "Поставщик найден в базе") 
                        : "Введите наименование вручную"
                    }
                    sx={{ backgroundColor: (foundSuppliers.length > 0 && !isManualMode) ? '#f5f5f5' : 'inherit' }}
                />
                
                {/* Кнопка переключения режима */}
                {foundSuppliers.length > 0 && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 0.5 }}>
                        <Link 
                            component="button" 
                            variant="body2" 
                            onClick={toggleManualMode}
                            underline="hover"
                            sx={{ display: 'flex', alignItems: 'center' }}
                        >
                            {isManualMode ? (
                                <><RefreshIcon fontSize="small" sx={{ mr: 0.5 }} /> Вернуться к найденному поставщику</>
                            ) : (
                                <><EditIcon fontSize="small" sx={{ mr: 0.5 }} /> Ввести вручную / Другое</>
                            )}
                        </Link>
                    </Box>
                )}
            </Box>
            
            {/* 2.1 Certificate Selection (если найдено > 1 и не ручной режим) */}
            {foundSuppliers.length > 1 && !isManualMode && (
                <Autocomplete
                    options={foundSuppliers}
                    getOptionLabel={(option) => `${option.product_name} (ВЦ: ${option.dvc_percent}%)`}
                    value={selectedCertificate}
                    onChange={handleCertificateSelect}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            label="Выберите товар из сертификата КТП"
                            required
                            fullWidth
                            helperText="У поставщика несколько сертификатов на этот код ЕНС ТРУ"
                            sx={{ mb: 2 }}
                        />
                    )}
                    renderOption={(props, option) => (
                        <li {...props} key={option.id}>
                            <Box>
                                <Typography variant="body1">{option.product_name}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                    ВЦ: {option.dvc_percent}% | {option.production_address}
                                </Typography>
                            </Box>
                        </li>
                    )}
                />
            )}
            
            {/* Display selected certificate info (если не ручной режим) */}
            {selectedCertificate && !isManualMode && (
                 <TextField
                    fullWidth
                    label="Наименование товара по СТ-KZ"
                    value={selectedCertificate.product_name}
                    InputProps={{
                        readOnly: true,
                    }}
                    helperText={`Внутристрановая ценность: ${selectedCertificate.dvc_percent}%`}
                    sx={{ mb: 2, backgroundColor: '#f0f4c3' }} // Light green background to indicate valid certificate
                />
            )}


            {/* 3. Contract Number и Contract Date в одной строке */}
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

            {/* 4. Quantity, Price, Sum в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                    fullWidth
                    type="number"
                    label={t('contract_quantity')}
                    value={contractQuantity}
                    onChange={(e) => setContractQuantity(e.target.value)}
                    required
                    // error={validation.isQuantityOverLimit} // Убрали валидацию по контракту
                    // helperText={validation.isQuantityOverLimit ? t('error_quantity_exceeds_plan') : ''}
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
                    value={currentContractSum.toFixed(2)}
                    disabled
                    // error={validation.isAmountOverLimit} // Убрали валидацию по контракту
                    // helperText={validation.isAmountOverLimit ? t('error_amount_exceeds_plan') : ''}
                    sx={{ flex: 1 }}
                />
            </Box>
            
            {/* 5. Fact VC Percentage */}
            <TextField
                fullWidth
                type="number"
                label={t('vc_mean_percent')}
                value={factVcPercentage}
                onChange={(e) => setFactVcPercentage(e.target.value)}
                required
                disabled={isVcDisabled} 
                error={validation.isVcPercentageInvalid}
                helperText={validation.isVcPercentageInvalid ? "Процент ВЦ должен быть от 0 до 100" : vcHelperText}
                sx={{ mb: 2, backgroundColor: isVcDisabled ? '#f5f5f5' : 'inherit' }}
            />

            {/* 6. Supply Volume Physical и Value в одной строке */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <TextField
                    fullWidth
                    type="number"
                    label={t('supply_volume_physical')}
                    value={supplyPhysical}
                    onChange={(e) => setSupplyPhysical(e.target.value)}
                    required
                    error={validation.isQuantityOverLimit || validation.isSupplyOverContract}
                    helperText={
                        validation.isQuantityOverLimit ? t('error_quantity_exceeds_plan') : 
                        (validation.isSupplyOverContract ? "Не может быть больше кол-ва по договору" : "")
                    }
                    sx={{ flex: 1 }}
                />
                <TextField
                    fullWidth
                    type="number"
                    label={t('supply_volume_value')}
                    value={currentSupplyValue.toFixed(2)}
                    disabled
                    error={validation.isAmountOverLimit}
                    helperText={validation.isAmountOverLimit ? t('error_amount_exceeds_plan') : ''}
                    sx={{ flex: 1 }}
                />
            </Box>

            {/* Кнопка добавления */}
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleSubmit}
                    disabled={validation.isQuantityOverLimit || validation.isPriceOverLimit || validation.isAmountOverLimit || validation.isBinInvalid || !supplierBin || validation.isVcPercentageInvalid || validation.isSupplyOverContract}
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

    const {executedQuantity, executedAmount} = useMemo(() => {
        return executions.reduce((acc, exec) => ({
            executedQuantity: acc.executedQuantity + Number(exec.supply_volume_physical),
            executedAmount: acc.executedAmount + Number(exec.supply_volume_value)
        }), {executedQuantity: 0, executedAmount: 0});
    }, [executions]);

    const remainingQuantity = planQuantity - executedQuantity;
    const remainingAmount = planAmount - executedAmount;

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
        >
            <DialogTitle sx={{pb: 2}}>
                {t('execution_report_title')}
                <Typography variant="subtitle2" color="text.secondary" component="div">{itemName}</Typography>
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
                value={Math.min((executedQuantity / planQuantity) * 100, 100)}
                color={executedQuantity > planQuantity ? 'error' : 'primary'}
                sx={{ height: 16, borderRadius: 8 }}
            />
            <Typography variant="caption" display="block" align="right" sx={{ mt: 0.5 }}>
                Факт поставки: {executedQuantity}
            </Typography>
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
                value={Math.min((executedAmount / planAmount) * 100, 100)}
                color={executedAmount > planAmount ? 'error' : 'primary'}
                sx={{ height: 16, borderRadius: 8 }}
            />
            <Typography variant="caption" display="block" align="right" sx={{ mt: 0.5 }}>
                Факт поставки: {formatMoney(executedAmount)}
            </Typography>
        </Box>
    </Box>
</Box>

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
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose}>{t('close')}</Button>
            </DialogActions>
        </Dialog>
    );
};

export default ExecutionModal;