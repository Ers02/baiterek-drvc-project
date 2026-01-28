import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Paper, CircularProgress, Alert, TextField,
  Autocomplete, Stack, FormControlLabel, Checkbox, Divider, Tooltip, Grid
} from '@mui/material';
import { useTranslation } from '../i18n/index.tsx';
import Header from '../components/Header';
import KatoModalSelect from '../components/KatoModalSelect';
import {
  getPlanById, updateItem, addItemToPlan, getEnstru, getCostItems,
  getSourceFunding, getAgsk, getMkei, checkKtp, PlanStatus, getItemById
} from '../services/api';
import type {
    PlanItemPayload, Enstru, CostItem, SourceFunding, Agsk, Mkei
} from '../services/api';
import { debounce } from 'lodash';

// Helper to format currency
const currencyFormatter = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'KZT' });
const formatCurrency = (amount: number) => currencyFormatter.format(amount);

// Define a special AGSK option for "Прайс-лист"
const PRICE_LIST_AGSK_OPTION = {
  id: -1, // Use a distinct ID that won't conflict with real IDs
  code: 'PRICE_LIST_NONE', // Use a distinct code
  name_ru: 'Прайс-лист',
  group: '',
};

export default function PlanItemForm() {
  const { planId, itemId } = useParams<{ planId: string; itemId: string }>();
  const navigate = useNavigate();
  const { t, lang } = useTranslation();
  const isEditMode = !!itemId;

  const [formData, setFormData] = useState<Record<string, any>>({
    resident_share: 100,
  });
  const [options, setOptions] = useState<Record<string, any[]>>({
    enstru: [], agsk: [], costItem: [], sourceFunding: [], mkei: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isFormLocked, setFormLocked] = useState(false);
  const [isEnstruSelected, setEnstruSelected] = useState(isEditMode);
  const [isKatoPurchaseModalOpen, setKatoPurchaseModalOpen] = useState(false);
  const [isKatoDeliveryModalOpen, setKatoDeliveryModalOpen] = useState(false);

  const showAgskField = formData.expense_item?.name_ru === 'СМР';
  const isGoods = formData.enstru?.type_name === 'GOODS'; // Определяем, является ли текущий Enstru товаром

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [costItems, sourceFunding, agskOptions] = await Promise.all([
          getCostItems(),
          getSourceFunding(),
          getAgsk(),
        ]);

        let finalAgskOptions = [PRICE_LIST_AGSK_OPTION, ...agskOptions];

        if (isEditMode) {
          const itemData = await getItemById(Number(itemId));

          // Handle AGSK logic specifically
          if (itemData.expense_item?.name_ru === 'СМР') {
            // If an AGSK object exists on the item...
            if (itemData.agsk) {
              // ...and it's not in our current list of options, add it.
              const isAgskInOptions = finalAgskOptions.some(opt => opt.code === itemData.agsk.code);
              if (!isAgskInOptions) {
                finalAgskOptions = [itemData.agsk, ...finalAgskOptions];
              }
            } else {
              // If there's no AGSK object, it must be "Прайс-лист"
              itemData.agsk = PRICE_LIST_AGSK_OPTION;
            }
          }
          
          setFormData(itemData);
          setEnstruSelected(true);
          if (itemData.version.status !== PlanStatus.DRAFT) {
            setFormLocked(true);
          }
        } else {
          const planData = await getPlanById(Number(planId));
          const activeVersion = planData.versions.find(v => v.is_active);
          if (activeVersion?.status !== PlanStatus.DRAFT) {
            setFormLocked(true);
          }
        }

        setOptions({
          costItem: costItems,
          sourceFunding,
          agsk: finalAgskOptions,
          enstru: [],
          mkei: []
        });

      } catch (err) {
        setError(t('error_loading_data'));
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [itemId, planId, isEditMode, t]);

  const debouncedFetch = useMemo(() =>
    debounce(async (query: string, fetcher: (q: string) => Promise<any[]>, key: string) => {
      if (query.length < 2) return;
      const data = await fetcher(query);
      // Если это АГСК, добавляем "Прайс-лист" к результатам поиска
      if (key === 'agsk') {
        setOptions(prev => ({ ...prev, agsk: [PRICE_LIST_AGSK_OPTION, ...data] }));
      } else {
        setOptions(prev => ({ ...prev, [key]: data }));
      }
    }, 500), []);

  const handleEnstruSelect = useCallback(async (value: Enstru | null) => {
    if (value) {
      const ktpStatus = await checkKtp(value.code).catch(() => ({ is_ktp: false }));
      setFormData(prev => {
        const newState = {
          ...prev,
          enstru: value,
          is_ktp: ktpStatus.is_ktp,
          // Сбрасываем долю при смене ЕНС ТРУ
          resident_share: 100,
          non_resident_reason: '',
        };
        // Если тип меняется на не-товары, очищаем unit и ставим количество 1
        if (value.type_name !== 'GOODS') {
          newState.unit = null;
          newState.unit_id = null; // Убедимся, что unit_id тоже очищен
          newState.quantity = 1;
        }
        return newState;
      });
      setEnstruSelected(true);
    } else {
      setFormData(prev => ({ ...prev, enstru: null, is_ktp: false, unit: null, unit_id: null, resident_share: 100, non_resident_reason: '' }));
      setEnstruSelected(false);
    }
  }, []);

  const handleSave = async () => {
    if (isFormLocked) return;
    
    // Валидация обязательных полей
    let formError = '';

    if (!formData.enstru?.code) formError = t('error_enstru_required');
    else if (!formData.expense_item?.id) formError = t('error_expense_item_required');
    else if (!formData.funding_source?.id) formError = t('error_funding_source_required');
    else if (isGoods && !formData.unit?.id) formError = t('error_unit_required_for_goods'); // Условная валидация
    else if (!formData.kato_purchase?.id) formError = t('error_kato_purchase_required');
    else if (!formData.kato_delivery?.id) formError = t('error_kato_delivery_required');
    else if (!formData.additional_specs || (typeof formData.additional_specs === 'string' && !formData.additional_specs.trim())) formError = t('error_additional_specs_required');
    else if (!formData.additional_specs_kz || (typeof formData.additional_specs_kz === 'string' && !formData.additional_specs_kz.trim())) formError = t('error_additional_specs_kz_required');
    // Валидация АГСК: если showAgskField, то agsk должен быть выбран (либо реальный, либо "Прайс-лист")
    else if (showAgskField && !formData.agsk) formError = t('error_agsk_required_for_smr');
    else if (!formData.quantity || Number(formData.quantity) <= 0) formError = t('error_quantity_required');
    else if (!formData.price_per_unit || Number(formData.price_per_unit) <= 0) formError = t('error_price_required');
    
    // Валидация доли местного содержания
    if (!isGoods) {
        if (formData.resident_share === undefined || formData.resident_share === null || formData.resident_share === '') {
            formError = t('error_resident_share_required');
        } else if (Number(formData.resident_share) < 100 && (!formData.non_resident_reason || !formData.non_resident_reason.trim())) {
            formError = t('error_non_resident_reason_required');
        }
    }

    if (formError) {
      setError(formError);
      return;
    }

    const payload: PlanItemPayload = {
      trucode: formData.enstru.code,
      unit_id: isGoods ? formData.unit?.id : null, // Отправляем unit_id только для товаров
      expense_item_id: formData.expense_item.id,
      funding_source_id: formData.funding_source.id,
      // Если выбран "Прайс-лист", отправляем null, иначе - код АГСК
      agsk_id: formData.agsk?.code === PRICE_LIST_AGSK_OPTION.code ? null : formData.agsk?.code,
      kato_purchase_id: formData.kato_purchase?.id,
      kato_delivery_id: formData.kato_delivery?.id,
      additional_specs: formData.additional_specs,
      additional_specs_kz: formData.additional_specs_kz,
      quantity: Number(formData.quantity) || 0,
      price_per_unit: Number(formData.price_per_unit) || 0,
      is_ktp: isGoods ? (formData.is_ktp || false) : Number(formData.resident_share) === 100,
      resident_share: isGoods ? 100 : Number(formData.resident_share),
      non_resident_reason: isGoods ? null : (Number(formData.resident_share) < 100 ? formData.non_resident_reason : null),
      min_dvc_percent: isGoods ? 100 : Number(formData.resident_share),
    };

    try {
      if (isEditMode) {
        await updateItem(Number(itemId), payload);
        navigate(`/plans/${formData.version.plan_id}`);
      } else {
        await addItemToPlan(Number(planId), payload);
        navigate(`/plans/${planId}`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || t('error_saving'));
    }
  };

  const itemTotal = useMemo(() => 
    (Number(formData.quantity) || 0) * (Number(formData.price_per_unit) || 0), 
  [formData.quantity, formData.price_per_unit]);

  // Функция для отображения типа потребности
  const getNeedTypeName = (typeName: string) => {
      if (typeName === 'GOODS') return t('need_type_goods');
      if (typeName === 'WORK' || typeName === 'WORKS') return t('need_type_works');
      if (typeName === 'SERVICE' || typeName === 'SERVICES') return t('need_type_services');
      return typeName;
  };

  if (loading) return <><Header /><CircularProgress /></>;

  return (
    <>
      <Header />
      <Box sx={{ p: 4, maxWidth: 'lg', mx: 'auto' }}>
        <Paper sx={{ p: 5 }}>
          <Typography variant="h5" gutterBottom>{isEditMode ? t('item_form_edit_title') : t('item_form_new_title')}</Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
          {isFormLocked && <Alert severity="warning" sx={{ mb: 2 }}>{t('form_locked_warning')}</Alert>}

          <Stack spacing={3} sx={{ mt: 3 }}>
            <Autocomplete
              disabled={isFormLocked || (isEditMode && isEnstruSelected)}
              options={options.enstru || []}
              isOptionEqualToValue={(o, v) => o.id === v.id}
              getOptionLabel={(o) => `${o.code} - ${lang === 'kk' ? o.name_kaz : o.name_rus}`}
              onInputChange={(_, v) => debouncedFetch(v, getEnstru, 'enstru')}
              onChange={(_, v) => handleEnstruSelect(v as Enstru | null)}
              value={formData.enstru || null}
              renderInput={(params) => <TextField {...params} label={t('enstru_label')} required />}
              filterOptions={(x) => x}
              renderOption={(props, option) => (
                <Tooltip
                  title={lang === 'kk' ? (option.detail_kaz || '') : (option.detail_rus || '')}
                  placement="right"
                  arrow
                  key={option.id}
                >
                  <li {...props} style={{ whiteSpace: 'nowrap' }}>
                    {`${option.code} - ${lang === 'kk' ? option.name_kaz : option.name_rus}`}
                  </li>
                </Tooltip>
              )}
            />

            {isEnstruSelected && (
              <>
                <Divider />
                <TextField 
                    label={t('need_type')} 
                    value={getNeedTypeName(formData.enstru?.type_name || '')} 
                    InputProps={{ readOnly: true }} 
                    variant="filled" 
                />
                
                {/* Характеристика из справочника */}
                <TextField 
                    label={t('enstru_specs_label')} 
                    value={lang === 'kk' ? (formData.enstru?.detail_kaz || '') : (formData.enstru?.detail_rus || '')} 
                    InputProps={{ readOnly: true }} 
                    variant="filled" 
                    multiline 
                    minRows={2}
                />

                {/* Дополнительная характеристика (ввод пользователя) */}
                <TextField 
                    label={t('additional_specs')} 
                    value={formData.additional_specs || ''} 
                    onChange={e => setFormData(prev => ({ ...prev, additional_specs: e.target.value }))}
                    disabled={isFormLocked}
                    multiline 
                    minRows={2}
                    required
                    error={!formData.additional_specs || (typeof formData.additional_specs === 'string' && !formData.additional_specs.trim())}
                />
                
                <TextField 
                    label={t('additional_specs_kz')} 
                    value={formData.additional_specs_kz || ''} 
                    onChange={e => setFormData(prev => ({ ...prev, additional_specs_kz: e.target.value }))}
                    disabled={isFormLocked}
                    multiline 
                    minRows={2}
                    required
                    error={!formData.additional_specs_kz || (typeof formData.additional_specs_kz === 'string' && !formData.additional_specs_kz.trim())}
                />
                
                {isGoods && ( // Условное отображение поля "Единица измерения"
                    <Autocomplete
                        disabled={isFormLocked}
                        options={options.mkei || []}
                        isOptionEqualToValue={(o, v) => o.id === v.id}
                        getOptionLabel={(o) => lang === 'kk' ? o.name_kz : o.name_ru}
                        onInputChange={(_, v) => debouncedFetch(v, getMkei, 'mkei')}
                        onChange={(_, v) => setFormData(prev => ({ ...prev, unit: v }))}
                        value={formData.unit || null}
                        renderInput={(params) => <TextField {...params} label={t('item_unit')} required={isGoods} />}
                        filterOptions={(x) => x}
                        noOptionsText={options.mkei.length === 0 ? "Начните вводить текст для поиска" : "Ничего не найдено"}
                    />
                )}

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField 
                        disabled={isFormLocked || !isGoods} 
                        label={t('item_quantity')} 
                        type="number" 
                        required 
                        fullWidth 
                        value={formData.quantity || ''} 
                        onChange={e => setFormData(prev => ({ ...prev, quantity: Number(e.target.value) }))} 
                        sx={{ backgroundColor: !isGoods ? '#f5f5f5' : 'inherit' }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField 
                        disabled={isFormLocked} 
                        label={t('item_price')} 
                        type="number" 
                        required 
                        fullWidth 
                        value={formData.price_per_unit || ''} 
                        onChange={e => setFormData(prev => ({ ...prev, price_per_unit: Number(e.target.value) }))} 
                    />
                  </Grid>
                </Grid>
                <TextField label={t('total_amount')} value={formatCurrency(itemTotal)} fullWidth InputProps={{ readOnly: true }} variant="filled" />

                <Divider />
                <Autocomplete 
                    disabled={isFormLocked} 
                    options={options.costItem || []} 
                    getOptionLabel={(o) => lang === 'kk' ? o.name_kz : o.name_ru} 
                    onChange={(_, v) => setFormData(prev => ({ ...prev, expense_item: v }))} 
                    value={formData.expense_item || null} 
                    renderInput={(params) => <TextField {...params} label={t('expense_item')} required />} 
                />
                
                {showAgskField && (
                  <Autocomplete
                    disabled={isFormLocked}
                    options={options.agsk || []}
                    isOptionEqualToValue={(option, value) => option.code === value.code}
                    getOptionLabel={(option) => {
                      if (option.code === PRICE_LIST_AGSK_OPTION.code) {
                        return PRICE_LIST_AGSK_OPTION.name_ru;
                      }
                      return `Группа: ${option.group}; Код: ${option.code}; ${option.name_ru}`;
                    }}
                    onInputChange={(_, v) => debouncedFetch(v, getAgsk, 'agsk')}
                    onChange={(_, v) => {
                      setFormData(prev => ({ ...prev, agsk: v }));
                    }}
                    value={formData.agsk || null}
                    renderInput={(params) => <TextField {...params} label={t('agsk_3')} required={showAgskField && formData.agsk === null} />}
                    filterOptions={(x) => x}
                    noOptionsText={options.agsk.length === 0 ? "Начните вводить текст для поиска (минимум 2 символа)" : "Ничего не найдено"}
                  />
                )}

                <Autocomplete 
                    disabled={isFormLocked} 
                    options={options.sourceFunding || []} 
                    getOptionLabel={(o) => lang === 'kk' ? o.name_kz : o.name_ru} 
                    onChange={(_, v) => setFormData(prev => ({ ...prev, funding_source: v }))} 
                    value={formData.funding_source || null} 
                    renderInput={(params) => <TextField {...params} label={t('funding_source')} required />} 
                />
                
                <TextField 
                    label={t('kato_purchase')} 
                    value={formData.kato_purchase ? (lang === 'kk' ? formData.kato_purchase.name_kz : formData.kato_purchase.name_ru) : ''} 
                    InputProps={{ readOnly: true }} 
                    onClick={() => !isFormLocked && setKatoPurchaseModalOpen(true)} 
                    disabled={isFormLocked} 
                    required 
                />
                <KatoModalSelect open={isKatoPurchaseModalOpen} onClose={() => setKatoPurchaseModalOpen(false)} onSelect={(kato) => setFormData(prev => ({ ...prev, kato_purchase: kato }))} currentValue={formData.kato_purchase || null} label={t('select_kato_purchase')} />

                <TextField 
                    label={t('kato_delivery')} 
                    value={formData.kato_delivery ? (lang === 'kk' ? formData.kato_delivery.name_kz : formData.kato_delivery.name_ru) : ''} 
                    InputProps={{ readOnly: true }} 
                    onClick={() => !isFormLocked && setKatoDeliveryModalOpen(true)} 
                    disabled={isFormLocked} 
                    required 
                />
                <KatoModalSelect open={isKatoDeliveryModalOpen} onClose={() => setKatoDeliveryModalOpen(false)} onSelect={(kato) => setFormData(prev => ({ ...prev, kato_delivery: kato }))} currentValue={formData.kato_delivery || null} label={t('select_kato_delivery')} />

                {isGoods && (
                    <FormControlLabel control={<Checkbox checked={formData.is_ktp || false} disabled />} label={t('is_ktp_label')} />
                )}
                
                {/* Блок доли местного содержания для Работ и Услуг */}
                {!isGoods && (
                    <>
                        <TextField
                            label={t('resident_share_label')}
                            type="number"
                            fullWidth
                            required
                            disabled={isFormLocked}
                            value={formData.resident_share}
                            onChange={(e) => {
                                const val = Number(e.target.value);
                                if (val >= 0 && val <= 100) {
                                    setFormData(prev => ({ ...prev, resident_share: val }));
                                }
                            }}
                            inputProps={{ min: 0, max: 100 }}
                            error={formData.resident_share === undefined || formData.resident_share === null || formData.resident_share === ''}
                        />
                        {Number(formData.resident_share) < 100 && (
                            <TextField
                                label={t('non_resident_reason_label')}
                                fullWidth
                                required
                                multiline
                                minRows={3}
                                disabled={isFormLocked}
                                value={formData.non_resident_reason || ''}
                                onChange={(e) => setFormData(prev => ({ ...prev, non_resident_reason: e.target.value }))}
                                error={!formData.non_resident_reason || !formData.non_resident_reason.trim()}
                            />
                        )}
                    </>
                )}

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, pt: 2 }}>
                  <Button variant="outlined" color="secondary" onClick={() => navigate(`/plans/${planId || formData.version.plan_id}`)}>{t('cancel')}</Button>
                  <Button variant="contained" onClick={handleSave} disabled={isFormLocked}>{t('save')}</Button>
                </Box>
              </>
            )}
          </Stack>
        </Paper>
      </Box>
    </>
  );
}
