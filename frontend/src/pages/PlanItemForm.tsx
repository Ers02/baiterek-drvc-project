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
const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'KZT' }).format(amount);

export default function PlanItemForm() {
  const { planId, itemId } = useParams<{ planId: string; itemId: string }>();
  const navigate = useNavigate();
  const { t, lang } = useTranslation();
  const isEditMode = !!itemId;

  const [formData, setFormData] = useState<Record<string, any>>({});
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

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [costItems, sourceFunding] = await Promise.all([getCostItems(), getSourceFunding()]);
        setOptions(prev => ({ ...prev, costItem: costItems, sourceFunding }));

        if (isEditMode) {
          const itemData = await getItemById(Number(itemId));
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
      setOptions(prev => ({ ...prev, [key]: data }));
    }, 500), []);

  const handleEnstruSelect = useCallback(async (value: Enstru | null) => {
    if (value) {
      const ktpStatus = await checkKtp(value.code).catch(() => ({ is_ktp: false }));
      setFormData(prev => ({
        ...prev,
        enstru: value,
        is_ktp: ktpStatus.is_ktp,
      }));
      setEnstruSelected(true);
    } else {
      setFormData(prev => ({ ...prev, enstru: null, is_ktp: false }));
      setEnstruSelected(false);
    }
  }, []);

  const handleSave = async () => {
    if (isFormLocked) return;
    
    // Валидация обязательных полей
    if (!formData.enstru?.code || !formData.expense_item?.id || !formData.funding_source?.id || !formData.unit?.id || !formData.kato_purchase?.id || !formData.kato_delivery?.id) {
      setError(t('error_fill_required_fields'));
      return;
    }
    if (showAgskField && !formData.agsk?.code) {
      setError(t('error_agsk_required_for_smr'));
      return;
    }

    const payload: PlanItemPayload = {
      trucode: formData.enstru.code,
      unit_id: formData.unit.id,
      expense_item_id: formData.expense_item.id,
      funding_source_id: formData.funding_source.id,
      agsk_id: formData.agsk?.code,
      kato_purchase_id: formData.kato_purchase?.id,
      kato_delivery_id: formData.kato_delivery?.id,
      quantity: Number(formData.quantity) || 0,
      price_per_unit: Number(formData.price_per_unit) || 0,
      is_ktp: formData.is_ktp || false,
      is_resident: formData.is_resident || false,
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
              getOptionLabel={(o) => `${o.code} - ${lang === 'ru' ? o.name_ru : o.name_kz}`}
              onInputChange={(_, v) => debouncedFetch(v, getEnstru, 'enstru')}
              onChange={(_, v) => handleEnstruSelect(v as Enstru | null)}
              value={formData.enstru || null}
              renderInput={(params) => <TextField {...params} label={t('enstru_label')} required />}
              filterOptions={(x) => x}
              renderOption={(props, option) => (
                <Tooltip
                  title={lang === 'ru' ? (option.specs_ru || '') : (option.specs_kz || '')}
                  placement="right"
                  arrow
                  key={option.id}
                >
                  <li {...props}>
                    {`${option.code} - ${lang === 'ru' ? option.name_ru : option.name_kz}`}
                  </li>
                </Tooltip>
              )}
            />

            {isEnstruSelected && (
              <>
                <Divider />
                <TextField label={t('need_type')} value={formData.enstru?.type_ru || ''} InputProps={{ readOnly: true }} variant="filled" />
                
                <TextField 
                    label={t('enstru_specs_label')} 
                    value={lang === 'ru' ? (formData.enstru?.specs_ru || '') : (formData.enstru?.specs_kz || '')} 
                    InputProps={{ readOnly: true }} 
                    variant="filled" 
                    multiline 
                    minRows={2}
                />
                
                <Autocomplete
                  disabled={isFormLocked}
                  options={options.mkei || []}
                  isOptionEqualToValue={(o, v) => o.id === v.id}
                  getOptionLabel={(o) => lang === 'ru' ? o.name_ru : o.name_kz}
                  onInputChange={(_, v) => debouncedFetch(v, getMkei, 'mkei')}
                  onChange={(_, v) => setFormData(prev => ({ ...prev, unit: v }))}
                  value={formData.unit || null}
                  renderInput={(params) => <TextField {...params} label={t('item_unit')} required />}
                  filterOptions={(x) => x}
                  noOptionsText={options.mkei.length === 0 ? "Начните вводить текст для поиска" : "Ничего не найдено"}
                />

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField 
                        disabled={isFormLocked} 
                        label={t('item_quantity')} 
                        type="number" 
                        required 
                        fullWidth 
                        value={formData.quantity || ''} 
                        onChange={e => setFormData(prev => ({ ...prev, quantity: Number(e.target.value) }))} 
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
                    getOptionLabel={(o) => lang === 'ru' ? o.name_ru : o.name_kz} 
                    onChange={(_, v) => setFormData(prev => ({ ...prev, expense_item: v }))} 
                    value={formData.expense_item || null} 
                    renderInput={(params) => <TextField {...params} label={t('expense_item')} required />} 
                />
                
                {showAgskField && (
                  <Autocomplete
                    disabled={isFormLocked}
                    options={options.agsk || []}
                    isOptionEqualToValue={(o, v) => o.id === v.id}
                    getOptionLabel={(o) => `Группа: ${o.group}; Код: ${o.code}; ${o.name_ru}`}
                    onInputChange={(_, v) => debouncedFetch(v, getAgsk, 'agsk')}
                    onChange={(_, v) => setFormData(prev => ({ ...prev, agsk: v }))}
                    value={formData.agsk || null}
                    renderInput={(params) => <TextField {...params} label={t('agsk_3')} required={showAgskField} />}
                    filterOptions={(x) => x}
                    noOptionsText={options.agsk.length === 0 ? "Начните вводить текст для поиска (минимум 2 символа)" : "Ничего не найдено"}
                  />
                )}

                <Autocomplete 
                    disabled={isFormLocked} 
                    options={options.sourceFunding || []} 
                    getOptionLabel={(o) => lang === 'ru' ? o.name_ru : o.name_kz} 
                    onChange={(_, v) => setFormData(prev => ({ ...prev, funding_source: v }))} 
                    value={formData.funding_source || null} 
                    renderInput={(params) => <TextField {...params} label={t('funding_source')} required />} 
                />
                
                <TextField 
                    label={t('kato_purchase')} 
                    value={formData.kato_purchase ? (lang === 'ru' ? formData.kato_purchase.name_ru : formData.kato_purchase.name_kz) : ''} 
                    InputProps={{ readOnly: true }} 
                    onClick={() => !isFormLocked && setKatoPurchaseModalOpen(true)} 
                    disabled={isFormLocked} 
                    required // Добавил required
                />
                <KatoModalSelect open={isKatoPurchaseModalOpen} onClose={() => setKatoPurchaseModalOpen(false)} onSelect={(kato) => setFormData(prev => ({ ...prev, kato_purchase: kato }))} currentValue={formData.kato_purchase || null} label={t('select_kato_purchase')} />

                <TextField 
                    label={t('kato_delivery')} 
                    value={formData.kato_delivery ? (lang === 'ru' ? formData.kato_delivery.name_ru : formData.kato_delivery.name_kz) : ''} 
                    InputProps={{ readOnly: true }} 
                    onClick={() => !isFormLocked && setKatoDeliveryModalOpen(true)} 
                    disabled={isFormLocked} 
                    required // Добавил required
                />
                <KatoModalSelect open={isKatoDeliveryModalOpen} onClose={() => setKatoDeliveryModalOpen(false)} onSelect={(kato) => setFormData(prev => ({ ...prev, kato_delivery: kato }))} currentValue={formData.kato_delivery || null} label={t('select_kato_delivery')} />

                <FormControlLabel control={<Checkbox checked={formData.is_ktp || false} disabled />} label={t('is_ktp_label')} />
                <FormControlLabel control={<Checkbox disabled={isFormLocked} checked={formData.is_resident || false} onChange={e => setFormData(prev => ({ ...prev, is_resident: e.target.checked }))} />} label={t('is_resident_label')} />

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
