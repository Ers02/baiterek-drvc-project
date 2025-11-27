import { useEffect, useState } from 'react'
import {
  Box, Paper, Typography, TextField, Button, Alert, CircularProgress,
  InputAdornment, Stack, Chip, FormControlLabel, Checkbox, MenuItem, Autocomplete
} from '@mui/material'
import { Search as SearchIcon, Calculate as CalculateIcon, Inventory as InventoryIcon } from '@mui/icons-material'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import Header from '../components/Header'
import { useLang, t } from '../i18n'

const ENSTRU_MOCK = [
  { code: '03111000-7', name: 'Пшеница мягкая', nameKk: 'Жұмсақ бидай', specs: 'Класс 3, влажность ≤14%', specsKk: '3-класс, ылғалдылық ≤14%', unit: 'т' },
  { code: '42122110-1', name: 'Насос центробежный', nameKk: 'Центрден қашыр насос', specs: '100 м³/ч, напор 50 м', specsKk: '100 м³/сағ, қысым 50 м', unit: 'шт' },
  { code: '45111100-9', name: 'Услуги по строительству дорог', nameKk: 'Жол салу қызметтері', specs: 'Асфальт, 12 см', specsKk: 'Асфальт, 12 см', unit: 'м²' },
  { code: '72211000-7', name: 'Разработка ПО', nameKk: 'Бағдарлама әзірлеу', specs: 'Веб-приложение', specsKk: 'Веб-қосымша', unit: 'усл' },
  { code: '34110000-1', name: 'Легковые автомобили', nameKk: 'Жеңіл автокөліктер', specs: 'Седан, до 2.0 л', specsKk: 'Седан, 2.0 л дейін', unit: 'шт' },
]

const KATO_LIST = [
  { code: '710000000', name: 'г. Астана', nameKk: 'Астана қ.' },
  { code: '750000000', name: 'г. Алматы', nameKk: 'Алматы қ.' },
  { code: '790000000', name: 'г. Шымкент', nameKk: 'Шымкент қ.' },
]

interface FormData {
  need_type: string
  enstru_code: string
  enstru_name: string
  enstru_specs: string
  additional_specs: string
  agsk_3: string
  expense_item: string
  funding_source: string
  kato_purchase: string
  kato_delivery: string
  unit: string
  quantity: number
  marketing_price: number
  is_ktp: boolean
  ktp_applicable: boolean
  number?: number
  state?: string
}

export default function ApplicationForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id
  const [lang] = useLang()

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState<FormData>({
    need_type: '', enstru_code: '', enstru_name: '', enstru_specs: '', additional_specs: '',
    agsk_3: '', expense_item: '', funding_source: '', kato_purchase: '', kato_delivery: '',
    unit: '', quantity: 0, marketing_price: 0, is_ktp: false, ktp_applicable: false
  })

  const total = form.quantity * form.marketing_price
  const currentEnstru = ENSTRU_MOCK.find(i => i.code === form.enstru_code)

  useEffect(() => {
    if (isEdit && id) loadApplication()
  }, [id, isEdit])

  const loadApplication = async () => {
    try {
      setLoading(true)
      const res = await api.get(`/applications/${id}`)
      setForm(res.data)
    } catch {
      setError(t('error_load'))
    } finally {
      setLoading(false)
    }
  }

  const handleEnstruSelect = (value: any) => {
    if (value) {
      setForm(prev => ({
        ...prev,
        enstru_code: value.code,
        enstru_name: lang === 'ru' ? value.name : value.nameKk || value.name,
        enstru_specs: lang === 'ru' ? value.specs : value.specsKk || value.specs,
        unit: value.unit,
      }))
    } else {
      setForm(prev => ({ ...prev, enstru_code: '', enstru_name: '', enstru_specs: '', unit: '' }))
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const payload = { ...form, planned_total_no_vat: total }
      if (isEdit) await api.put(`/applications/${id}`, payload)
      else await api.post('/applications', payload)
      navigate('/')
    } catch { setError(t('error_save')) } finally { setSaving(false) }
  }

  const handleSubmit = async () => {
    try {
      await api.post(`/applications/${id}/state/submitted`)
      navigate('/')
    } catch { setError(t('error_submit')) }
  }

  if (loading) return <><Header /><Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}><CircularProgress size={80} /></Box></>

  return (
    <>
      <Header />
      <Box maxWidth="lg" mx="auto" px={3} py={4}>
        <Typography variant="h4" fontWeight="bold" color="primary" mb={2}>
          {isEdit ? t('edit_application', { number: form.number || id || '' }) : t('create_application')}
        </Typography>

        {form.state && <Chip label={form.state === 'draft' ? t('draft') : t('submitted')} color={form.state === 'draft' ? 'default' : 'primary'} sx={{ mb: 3 }} />}

        {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>{error}</Alert>}

        <Paper elevation={8} sx={{ p: 5, borderRadius: 3, bgcolor: '#f9fff9' }}>
          <Box mb={6}>
            <Typography variant="h6" fontWeight="bold" color="primary" mb={2}>{t('enstru_search')}</Typography>
            <Autocomplete
              options={ENSTRU_MOCK}
              getOptionLabel={opt => `${opt.code} — ${lang === 'ru' ? opt.name : opt.nameKk || opt.name}`}
              value={currentEnstru || null}
              onChange={(_, v) => handleEnstruSelect(v)}
              renderInput={params => (
                <TextField {...params} placeholder={t('enstru_placeholder')} fullWidth required
                  InputProps={{ ...params.InputProps, startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
                />
              )}
            />
          </Box>

          {form.enstru_code && currentEnstru ? (
            <>
              <Paper sx={{ p: 4, mb: 5, bgcolor: '#e8f5e9', borderRadius: 2 }}>
                <Typography fontWeight="bold" color="success.dark" mb={2}>{t('enstru_data')}</Typography>
                <Stack spacing={3}>
                  <TextField label={t('enstru_name')} value={form.enstru_name} InputProps={{ readOnly: true }} fullWidth />
                  <TextField label={t('enstru_specs')} value={form.enstru_specs} multiline rows={2} InputProps={{ readOnly: true }} fullWidth />
                  <TextField label={t('enstru_unit')} value={form.unit} InputProps={{ readOnly: true }} fullWidth />
                </Stack>
              </Paper>

              <Typography variant="h6" fontWeight="bold" color="primary" mb={3}>{t('fill_form')}</Typography>

              <Stack spacing={3}>
                <TextField select label={t('need_type')} required fullWidth value={form.need_type} onChange={e => setForm(p => ({ ...p, need_type: e.target.value }))}>
                  <MenuItem value="Товар">{t('need_type_goods')}</MenuItem>
                  <MenuItem value="Работа">{t('need_type_works')}</MenuItem>
                  <MenuItem value="Услуга">{t('need_type_services')}</MenuItem>
                </TextField>

                <TextField label={t('additional_specs')} multiline rows={3} fullWidth value={form.additional_specs} onChange={e => setForm(p => ({ ...p, additional_specs: e.target.value }))} />
                <TextField label={t('agsk_3')} fullWidth value={form.agsk_3} onChange={e => setForm(p => ({ ...p, agsk_3: e.target.value }))} />
                <TextField select label={t('funding_source')} required fullWidth value={form.funding_source} onChange={e => setForm(p => ({ ...p, funding_source: e.target.value }))}>
                  <MenuItem value="Республиканский бюджет">{t('republic_budget')}</MenuItem>
                  <MenuItem value="Местный бюджет">{t('local_budget')}</MenuItem>
                  <MenuItem value="Собственные средства">{t('own_funds')}</MenuItem>
                </TextField>

                <TextField select label={t('kato_purchase')} fullWidth value={form.kato_purchase} onChange={e => setForm(p => ({ ...p, kato_purchase: e.target.value }))}>
                  {KATO_LIST.map(k => <MenuItem key={k.code} value={k.code}>{lang === 'ru' ? k.name : k.nameKk}</MenuItem>)}
                </TextField>

                <TextField select label={t('kato_delivery')} fullWidth value={form.kato_delivery} onChange={e => setForm(p => ({ ...p, kato_delivery: e.target.value }))}>
                  {KATO_LIST.map(k => <MenuItem key={k.code} value={k.code}>{lang === 'ru' ? k.name : k.nameKk}</MenuItem>)}
                </TextField>

                <TextField label={t('quantity')} type="number" required fullWidth value={form.quantity || ''} onChange={e => setForm(p => ({ ...p, quantity: Number(e.target.value) || 0 }))} />
                <TextField label={t('price')} type="number" fullWidth value={form.marketing_price || ''} onChange={e => setForm(p => ({ ...p, marketing_price: Number(e.target.value) || 0 }))} InputProps={{ endAdornment: <InputAdornment position="end">₸</InputAdornment> }} />
                <TextField label={t('total')} value={total.toLocaleString('ru-RU')} fullWidth InputProps={{ readOnly: true, startAdornment: <InputAdornment position="start"><CalculateIcon color="success" /></InputAdornment>, endAdornment: <InputAdornment position="end">₸</InputAdornment> }} sx={{ bgcolor: '#e8f5e9', fontWeight: 'bold' }} />

                <FormControlLabel control={<Checkbox checked={form.is_ktp} onChange={e => setForm(p => ({ ...p, is_ktp: e.target.checked }))} />} label={t('is_ktp')} />
                {form.need_type === 'Товар' && <FormControlLabel control={<Checkbox checked={form.ktp_applicable} onChange={e => setForm(p => ({ ...p, ktp_applicable: e.target.checked }))} />} label={t('ktp_applicable')} />}
              </Stack>

              <Box mt={6} display="flex" gap={2} justifyContent="flex-end">
                <Button variant="outlined" size="large" onClick={() => navigate('/')}>{t('cancel')}</Button>
                <Button variant="contained" size="large" color="success" onClick={handleSave} disabled={saving}>
                  {saving ? t('saving') : t('save_draft')}
                </Button>
                {isEdit && <Button variant="contained" size="large" color="primary" onClick={handleSubmit}>{t('submit')}</Button>}
              </Box>
            </>
          ) : (
            <Box textAlign="center" py={12} color="text.secondary">
              <InventoryIcon sx={{ fontSize: 90, opacity: 0.3 }} />
              <Typography variant="h6" mt={3}>{t('select_first')}</Typography>
              <Typography>{t('will_appear')}</Typography>
            </Box>
          )}
        </Paper>
      </Box>
    </>
  )
}