import { useState, useEffect, useRef } from 'react';
import {
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Button, Tabs, Tab, Chip, IconButton, Dialog,
  DialogTitle, DialogContent, TextField, DialogActions, Tooltip,
  Pagination, Divider, Card, CardContent, InputAdornment,
  LinearProgress, CircularProgress, Stack, FormControlLabel, Switch,
  Avatar, ToggleButton, ToggleButtonGroup
} from '@mui/material';
import {
  Delete as DeleteIcon, Download as DownloadIcon,
  Search as SearchIcon, Refresh as RefreshIcon, Business as BusinessIcon,
  Close as CloseIcon, Edit as EditIcon,
  LocationOn as LocationOnIcon,
  Fingerprint as BinIcon, AutoAwesome as AutoIcon,
  QrCode as AgskIcon,
  Category as CategoryIcon,
  InfoOutlined as InfoIcon,
  LibraryBooks as LibraryIcon,
  FileDownload as FileDownloadIcon,
  Description as DescriptionIcon,
  UploadFile as UploadIcon,
  Science as ScienceIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Phone as PhoneIcon,
  AssignmentInd as AssignIcon,
  Group as GroupIcon,
  PersonOutline as PersonOutlineIcon,
  AccessTime as AccessTimeIcon,
  CheckCircle as CheckCircleIcon,
  Send as SendIcon
} from '@mui/icons-material';
import { useTranslation } from '../i18n';
import Header from '../components/Header';
import api from '../services/api';
import { calculateWorkingDays } from '../utils/dateUtils';

function useDebounce(value: any, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

const Highlight: React.FC<{ text: string; search: string }> = ({ text, search }) => {
  if (!search.trim() || !text) return <>{text}</>;
  const parts = text.split(new RegExp(`(${search.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi'));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === search.toLowerCase() ? (
          <Box component="span" key={i} sx={{ bgcolor: '#fff59d', color: '#000', borderRadius: '2px', px: '2px' }}>
            {part}
          </Box>
        ) : (
          part
        )
      )}
    </>
  );
};

interface AgskMatch {
  item_id: number;
  position_number: string;
  name: string;
  code_sn: string;
  unit: string;
  volume: number;
  enstru_code?: string;
  enstru_name?: string;
  match_type: 'auto' | 'manual' | 'manual_ktp' | 'auto_ktp' | 'none';
  match_score?: number;
  match_reason?: string;
}

interface LibraryItem {
  id: number;
  agsk_code: string;
  enstru_code: string;
  enstru_name_ru: string;
  product_name_ktp?: string;
  dvc_percent?: number;
}

interface ReestrResult {
  ktp_id: number;
  enstru_code: string;
  enstru_name: string;
  company: string;
  bin: string;
  product: string;
  dvc_percent: number;
  localization: string;
  address: string;
  registry_date: string;
  region: string;
  agsk3_codes?: string[];
  agsk3_names?: string[];
}

type SearchMode = 'all' | 'agsk' | 'name';

const SEARCH_TABS: { mode: SearchMode; label: string; placeholder: string }[] = [
  { mode: 'all',  label: 'Все',       placeholder: 'Поиск по всем полям...' },
  { mode: 'agsk', label: 'АГСК-код',  placeholder: 'Напр. 541-801 или 541-801-2066-58...' },
  { mode: 'name', label: 'Название',  placeholder: 'Название товара или компании...' },
];

const PsdAnalystPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(0);
  const [documents, setDocuments] = useState<any[]>([]);
  const [matches, setMatches] = useState<AgskMatch[]>([]);
  const [archive, setArchive] = useState<LibraryItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const [finishLoading, setFinishLoading] = useState(false);
  const [showTests, setShowTests] = useState(false);
  const [assignedToMe, setAssignedToMe] = useState(false);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingMatch, setEditingMatch] = useState<AgskMatch | null>(null);
  const [library, setLibrary] = useState<LibraryItem[]>([]);
  const [reestrResults, setReestrResults] = useState<ReestrResult[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);

  const [searchMode, setSearchMode] = useState<SearchMode>('all');
  const [reestrSearch, setReestrSearch] = useState('');
  const [agskSearch, setAgskSearch] = useState('');
  const [reestrLoading, setReestrLoading] = useState(false);

  const debouncedReestrSearch = useDebounce(reestrSearch, 400);
  const debouncedAgskSearch = useDebounce(agskSearch, 500);

  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [onlyUnmatched, setOnlyUnmatched] = useState(false);

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [testProjectName, setTestProjectName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const requestCounter = useRef(0);

  useEffect(() => { loadDocuments(); loadArchive(); }, [showTests, assignedToMe]);

  useEffect(() => {
    if (selectedDoc) loadMatches(selectedDoc.id);
  }, [selectedDoc, onlyUnmatched, page, debouncedAgskSearch]);

  useEffect(() => { setReestrSearch(''); setReestrResults([]); }, [searchMode]);

  useEffect(() => {
    const minLen = searchMode === 'agsk' ? 3 : 2;
    if (debouncedReestrSearch.length >= minLen) handleSearchReestr();
    else if (debouncedReestrSearch.length === 0) setReestrResults([]);
  }, [debouncedReestrSearch, searchMode]);

  const loadDocuments = async () => {
    const res = await api.get('/psd-analyst/documents', {
        params: { is_test: showTests, assigned_to_me: assignedToMe }
    });
    setDocuments(res.data);
  };
  const loadArchive = async () => {
    const res = await api.get('/psd-analyst/existing-matches');
    setArchive(res.data);
  };

  const loadMatches = async (docId: number) => {
    const currentRequestId = ++requestCounter.current;
    setListLoading(true);
    try {
      const res = await api.get(`/psd-analyst/document-items/${docId}`, {
        params: {
          only_unmatched: onlyUnmatched,
          skip: (page - 1) * 50,
          limit: 50,
          search: debouncedAgskSearch || undefined
        }
      });
      if (currentRequestId === requestCounter.current) {
        setMatches(res.data.items);
        setTotalCount(res.data.total);
      }
    } finally {
      if (currentRequestId === requestCounter.current) {
        setListLoading(false);
      }
    }
  };

  const handleDeleteDocument = async (docId: number) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот проект? Это действие необратимо.')) return;
    try {
        await api.delete(`/psd-analyst/documents/${docId}`);
        if (selectedDoc?.id === docId) setSelectedDoc(null);
        loadDocuments();
    } catch (err) {
        alert('Ошибка при удалении');
    }
  };

  const handleParse = async () => {
    if (!selectedDoc) return;
    setParsing(true);
    try {
      await api.post(`/psd-analyst/documents/${selectedDoc.id}/parse`);
      await loadMatches(selectedDoc.id);
    } finally { setParsing(false); }
  };

  const handleFinishAnalysis = async () => {
    if (!selectedDoc) return;
    if (!window.confirm('Завершить анализ? Это действие сформирует финальный отчет и отправит его дочерней организации по API (если настроено).')) return;
    
    setFinishLoading(true);
    try {
        await api.post(`/psd-analyst/documents/${selectedDoc.id}/finish`);
        alert('Анализ успешно завершен!');
        loadDocuments();
        setActiveTab(0);
        setSelectedDoc(null);
    } catch (err) {
        alert('Ошибка при завершении анализа');
    } finally {
        setFinishLoading(false);
    }
  };

  const handleUploadTest = async () => {
    if (!selectedFile || !testProjectName) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('project_name', testProjectName);

      const res = await api.post('/psd-analyst/upload-test', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setUploadDialogOpen(false);
      setTestProjectName('');
      setSelectedFile(null);
      
      // Переключаемся на тесты и загружаем список
      setShowTests(true);
      await loadDocuments();
      
      // Открываем созданный документ
      if (res.data) {
        setSelectedDoc(res.data);
        setActiveTab(1);
      }
    } catch (err) {
      alert('Ошибка при загрузке: ' + err);
    } finally {
      setUploading(false);
    }
  };

  const openEditDialog = async (match: AgskMatch) => {
    setEditingMatch(match);
    setEditDialogOpen(true);
    setSearchMode('all');
    setReestrSearch('');
    setReestrResults([]);
    const [libRes, recRes] = await Promise.all([
      api.get(`/psd-analyst/agsk-library/${match.code_sn}`),
      api.get('/psd-analyst/suggest-enstru-for-agsk', { params: { agsk_code: match.code_sn } }),
    ]);
    setLibrary(libRes.data);
    setRecommendations(recRes.data);
  };

  const handleSearchReestr = async () => {
    setReestrLoading(true);
    try {
      const res = await api.get('/psd-analyst/search-enstru-reestr', {
        params: {
          query: debouncedReestrSearch,
          search_mode: searchMode,
        }
      });
      setReestrResults(res.data);
    } finally { setReestrLoading(false); }
  };

  const addToLibrary = async (item: ReestrResult, type: 'rec' | 'ktp') => {
    if (!editingMatch) return;
    await api.post('/psd-analyst/manual-match', {
      agsk_code: editingMatch.code_sn,
      enstru_code: item.enstru_code,
      ktp_id: item.ktp_id || null,
      dvc_percent: item.dvc_percent || 0,
      product_name_ktp: item.product || null,
      doc_id: selectedDoc?.id,
    });
    const libRes = await api.get(`/psd-analyst/agsk-library/${editingMatch.code_sn}`);
    setLibrary(libRes.data);
    loadArchive();
    loadMatches(selectedDoc.id);

    // Remove the added item from recommendations and reestrResults
    setRecommendations(prev => prev.filter(rec => !(rec.enstru_code === item.enstru_code && rec.ktp_id === item.ktp_id)));
    setReestrResults(prev => prev.filter(res => !(res.enstru_code === item.enstru_code && res.ktp_id === item.ktp_id)));
  };

  const removeFromLibrary = async (id: number) => {
    await api.delete(`/psd-analyst/agsk-library/${id}`);
    if (editingMatch) {
      const libRes = await api.get(`/psd-analyst/agsk-library/${editingMatch.code_sn}`);
      setLibrary(libRes.data);
    }
    loadArchive();
    if (selectedDoc) loadMatches(selectedDoc.id);
  };

  const handleExportFullReport = async (docId?: number) => {
    setExportLoading(true);
    try {
      const response = await api.get('/psd-analyst/export-full-report', {
        params: { doc_id: docId },
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = docId ? `psd_report_doc_${docId}.xlsx` : 'psd_full_report.xlsx';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Ошибка при выгрузке отчета');
    } finally {
      setExportLoading(false);
    }
  };

  const handleDownloadConclusion = async (docId: number) => {
    setDocxLoading(true);
    try {
      const response = await api.get(`/psd-analyst/documents/${docId}/conclusion`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Заключение_ПСД_${docId}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download conclusion failed:', error);
      alert('Ошибка при генерации заключения');
    } finally {
      setDocxLoading(false);
    }
  };

  const getMatchTypeStyles = (type: string) => {
    switch (type) {
      case 'manual_ktp': return { label: 'КТП + Библиотека', color: 'primary' };
      case 'manual':     return { label: 'Библиотека',      color: 'success' };
      case 'auto':       return { label: 'Авто',            color: 'info' };
      case 'auto_ktp':   return { label: 'КТП',             color: 'warning' };
      default:           return { label: 'Нет',             color: 'error' };
    }
  };

  const getDvcColor = (percent: number) => {
    if (percent === 100) return 'success';
    if (percent >= 70)   return 'warning';
    return 'default';
  };

  const AgskChips: React.FC<{ codes?: string[]; names?: string[]; highlight?: string }> = ({
    codes = [], names = [], highlight = ''
  }) => {
    if (!codes.length) return null;
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
        {codes.map((code, i) => {
          const name = names[i] || '';
          const isMatch = highlight && code.toLowerCase().includes(highlight.toLowerCase()); // Use includes for broader highlighting
          return (
            <Tooltip key={code} title={name || code} arrow placement="top">
              <Chip
                label={<Highlight text={code} search={highlight} />}
                size="small"
                icon={<AgskIcon sx={{ fontSize: '10px !important' }} />}
                sx={{
                  height: 20,
                  fontSize: '0.6rem',
                  fontFamily: 'monospace',
                  cursor: 'default',
                  bgcolor: isMatch ? '#e8f5e9' : '#f0f4f8',
                  borderColor: isMatch ? '#4caf50' : '#cfd8dc',
                  border: '1px solid',
                  color: isMatch ? '#2e7d32' : '#455a64',
                  fontWeight: isMatch ? 'bold' : 'normal',
                  '& .MuiChip-icon': { color: isMatch ? '#4caf50' : '#90a4ae' }
                }}
              />
            </Tooltip>
          );
        })}
      </Box>
    );
  };

  const currentSearchTab = SEARCH_TABS.find(t => t.mode === searchMode)!;

  return (
    <Box sx={{ bgcolor: '#f5f7f9', minHeight: '100vh' }}>
      <Header />
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h5" fontWeight="bold" color="#1a237e">
              Аналитика ПСД
            </Typography>

            <Divider orientation="vertical" flexItem sx={{ mx: 1, height: 24, alignSelf: 'center' }} />

            <ToggleButtonGroup
              size="small"
              value={assignedToMe}
              exclusive
              onChange={(_, v) => v !== null && setAssignedToMe(v)}
              sx={{ bgcolor: 'white' }}
            >
                <ToggleButton value={false} sx={{ px: 2, textTransform: 'none', gap: 1 }}>
                    <GroupIcon fontSize="small" /> Все проекты
                </ToggleButton>
                <ToggleButton value={true} sx={{ px: 2, textTransform: 'none', gap: 1 }}>
                    <PersonOutlineIcon fontSize="small" /> Мои
                </ToggleButton>
            </ToggleButtonGroup>

            <FormControlLabel
              control={
                <Switch 
                  checked={showTests} 
                  onChange={(e) => setShowTests(e.target.checked)} 
                  color="warning" 
                  size="small"
                />
              }
              label={
                <Typography sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: showTests ? 'warning.main' : 'text.secondary' }}>
                  Тестовые
                </Typography>
              }
              sx={{ ml: 1, bgcolor: showTests ? '#fff3e0' : 'transparent', px: 1.5, borderRadius: 5, py: 0.2, border: '1px solid', borderColor: showTests ? 'warning.light' : 'transparent' }}
            />
          </Box>
          
          <Stack direction="row" spacing={1}>
            <Button 
                size="small" 
                variant="outlined" 
                color="warning"
                startIcon={<ScienceIcon />} 
                onClick={() => setUploadDialogOpen(true)}
                sx={{ bgcolor: 'white', textTransform: 'none' }}>
              Создать тест
            </Button>
            <Button size="small" variant="outlined" startIcon={<RefreshIcon />} onClick={loadDocuments}
              sx={{ bgcolor: 'white', textTransform: 'none' }}>
              Обновить
            </Button>
            <Button 
              size="small" 
              variant="contained" 
              startIcon={exportLoading ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
              disabled={exportLoading}
              onClick={() => handleExportFullReport()} 
              sx={{ textTransform: 'none' }}
            >
              Экспорт всех
            </Button>
          </Stack>
        </Box>

        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}
          sx={{ mb: 2, bgcolor: 'white', borderRadius: 2, minHeight: 40 }}>
          <Tab label="Документы"     sx={{ textTransform: 'none', minHeight: 40 }} />
          <Tab label="Рабочая область" disabled={!selectedDoc} sx={{ textTransform: 'none', minHeight: 40 }} />
          <Tab label="Архив"         sx={{ textTransform: 'none', minHeight: 40 }} />
        </Tabs>

        {activeTab === 0 && (
          <TableContainer component={Paper} elevation={0}
            sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Table size="small">
              <TableHead sx={{ bgcolor: '#fafafa' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Наименование / Отправитель</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Аналитик</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Рабочих дней</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Статус</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Действие</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map(doc => {
                  const days = calculateWorkingDays(doc.received_at, doc.completed_at || new Date());
                  const isOverdue = days > 10 && doc.status !== 'COMPLETED';
                  
                  return (
                    <TableRow key={doc.id} hover sx={{ bgcolor: doc.is_test ? '#fffef0' : 'inherit' }}>
                      <TableCell>#{doc.id}</TableCell>
                      <TableCell>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {doc.is_test && <ScienceIcon sx={{ fontSize: 16, color: 'warning.main' }} />}
                                  <Typography variant="body2" fontWeight="bold">{doc.bank_name}</Typography>
                              </Box>
                              {(doc.sender_last_name || doc.sender_first_name) && (
                                  <Tooltip title={`${doc.sender_last_name || ''} ${doc.sender_first_name || ''} ${doc.sender_patronymic || ''}`}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                          <PersonIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                                          <Typography variant="caption" color="text.secondary">
                                              {doc.sender_last_name} {doc.sender_first_name?.charAt(0)}.
                                          </Typography>
                                      </Box>
                                  </Tooltip>
                              )}
                          </Box>
                      </TableCell>
                      <TableCell>
                          {doc.assigned_user_name ? (
                              <Chip 
                                  size="small" 
                                  icon={<PersonIcon sx={{ fontSize: '14px !important' }} />} 
                                  label={doc.assigned_user_name} 
                                  variant="outlined"
                                  color="primary"
                                  sx={{ borderRadius: 1 }}
                              />
                          ) : (
                              <Typography variant="caption" color="text.disabled">Не назначен</Typography>
                          )}
                      </TableCell>
                      <TableCell>
                        <Chip 
                            icon={<AccessTimeIcon sx={{ fontSize: '14px !important' }} />}
                            label={`${days} раб. дн.`} 
                            color={isOverdue ? 'error' : 'default'} 
                            variant={isOverdue ? 'filled' : 'outlined'}
                            size="small" 
                            sx={{ fontWeight: 'bold' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip 
                            label={doc.status} 
                            size="small" 
                            variant="outlined" 
                            color={doc.status === 'ERROR' ? 'error' : (doc.status === 'COMPLETED' ? 'success' : 'default')} 
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          {!doc.assigned_to ? (
                              <Button size="small" variant="contained" startIcon={<AssignIcon />}
                              onClick={() => api.post(`/psd-analyst/documents/${doc.id}/assign`).then(loadDocuments)}>
                              Взять в работу
                              </Button>
                          ) : (
                              <Button size="small" variant="outlined"
                              onClick={() => { setSelectedDoc(doc); setActiveTab(1); }}>
                              Открыть
                              </Button>
                          )}
                          <IconButton size="small" color="error" onClick={() => handleDeleteDocument(doc.id)}>
                              <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {documents.length === 0 && (
                    <TableRow>
                        <TableCell colSpan={6} align="center" sx={{ py: 5 }}>
                            <Typography color="text.secondary">
                                {assignedToMe ? 'У вас нет проектов в работе' : (showTests ? 'Тестовые проекты не найдены' : 'Документы не найдены')}
                            </Typography>
                        </TableCell>
                    </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {activeTab === 1 && selectedDoc && (
          <Box>
            <Paper sx={{ 
                p: 1.5, mb: 2, display: 'flex', gap: 2, alignItems: 'center', 
                borderRadius: 2, flexWrap: 'wrap',
                borderLeft: selectedDoc.is_test ? '6px solid #ffa000' : 'none'
            }}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {selectedDoc.is_test && <ScienceIcon sx={{ fontSize: 18, color: 'warning.main' }} />}
                    #{selectedDoc.id} {selectedDoc.bank_name}
                </Typography>
                {selectedDoc.is_test ? (
                    <Typography variant="caption" color="warning.dark" sx={{ fontWeight: 'bold' }}>
                        ТЕСТОВЫЙ РЕЖИМ (ДЛЯ СЕБЯ)
                    </Typography>
                ) : (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                         {selectedDoc.sender_last_name && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <PersonIcon sx={{ fontSize: 12 }} /> 
                                {selectedDoc.sender_last_name} {selectedDoc.sender_first_name}
                            </Typography>
                         )}
                         {selectedDoc.sender_phone && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <PhoneIcon sx={{ fontSize: 12 }} /> {selectedDoc.sender_phone}
                            </Typography>
                         )}
                    </Box>
                )}
              </Box>
              
              <Divider orientation="vertical" flexItem />
              
              <Chip 
                label={`Позиций: ${totalCount}`} 
                size="small" 
                color="primary" 
                variant="outlined" 
                sx={{ fontWeight: 'bold' }} 
              />
              
              <Divider orientation="vertical" flexItem />

              {totalCount === 0 ? (
                <Button size="small" variant="contained" color="warning" onClick={handleParse} disabled={parsing}>
                  {parsing ? 'Загрузка...' : 'Распарсить'}
                </Button>
              ) : (
                <>
                  <TextField
                    size="small" placeholder="Поиск по позициям..." value={agskSearch}
                    onChange={e => { setAgskSearch(e.target.value); setPage(1); }} sx={{ width: 250 }}
                    InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
                  />
                  <Button size="small" variant={onlyUnmatched ? 'contained' : 'outlined'} color="error"
                    onClick={() => { setOnlyUnmatched(!onlyUnmatched); setPage(1); }}>
                    Несопоставленные
                  </Button>
                  
                  <Box sx={{ flexGrow: 1 }} />
                  
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="secondary"
                      startIcon={docxLoading ? <CircularProgress size={16} color="inherit" /> : <DescriptionIcon />}
                      disabled={docxLoading}
                      onClick={() => handleDownloadConclusion(selectedDoc.id)}
                      sx={{ textTransform: 'none' }}
                    >
                      Заключение (DOCX)
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      color="success"
                      startIcon={exportLoading ? <CircularProgress size={16} color="inherit" /> : <FileDownloadIcon />}
                      disabled={exportLoading}
                      onClick={() => handleExportFullReport(selectedDoc.id)}
                      sx={{ textTransform: 'none' }}
                    >
                      Отчет (Excel)
                    </Button>
                    
                    {!selectedDoc.is_test && selectedDoc.status !== 'COMPLETED' && (
                        <Button
                            size="small"
                            variant="contained"
                            color="primary"
                            startIcon={finishLoading ? <CircularProgress size={16} color="inherit" /> : <CheckCircleIcon />}
                            disabled={finishLoading}
                            onClick={handleFinishAnalysis}
                            sx={{ textTransform: 'none' }}
                        >
                            Завершить и отправить
                        </Button>
                    )}
                    
                    {selectedDoc.status === 'COMPLETED' && (
                        <Chip icon={<CheckCircleIcon />} label="Анализ завершен" color="success" />
                    )}
                  </Stack>
                </>
              )}
            </Paper>

            <TableContainer component={Paper} sx={{ borderRadius: 2, border: '1px solid #e0e0e0', position: 'relative', minHeight: matches.length > 0 ? 'auto' : 200 }}>
              {listLoading && <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0 }} />}
              <Table size="small">
                <TableHead sx={{ bgcolor: '#fafafa' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold' }}>№</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Наименование</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>AGSK</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>ЕНС ТРУ</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Тип</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Действие</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {matches.map(m => (
                    <TableRow key={m.item_id} hover>
                      <TableCell>{m.position_number}</TableCell>
                      <TableCell sx={{ maxWidth: 450 }}>
                        <Tooltip title={m.name}>
                          <Typography variant="body2" sx={{ 
                            fontWeight: 600, 
                            color: '#2c3e50',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            lineHeight: 1.3
                          }}>
                            <Highlight text={m.name} search={debouncedAgskSearch} />
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        <Highlight text={m.code_sn} search={debouncedAgskSearch} />
                      </TableCell>
                      <TableCell sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {m.enstru_code || '—'}
                            {m.match_reason && (
                              <Tooltip title={m.match_reason}>
                                <InfoIcon sx={{ fontSize: 14, color: '#90a4ae', cursor: 'help' }} />
                              </Tooltip>
                            )}
                          </Box>
                          {(m.match_type === 'auto' || m.match_type === 'auto_ktp') && m.match_reason && (
                            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', lineHeight: 1.2 }}>
                              {m.match_reason}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={getMatchTypeStyles(m.match_type).label}
                          color={getMatchTypeStyles(m.match_type).color as any}
                          icon={m.match_type === 'manual_ktp' ? <LibraryIcon sx={{ fontSize: '12px !important' }} /> : undefined}
                          size="small" 
                          sx={{ fontSize: '0.7rem' }} 
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => openEditDialog(m)} sx={{ bgcolor: '#f0f4f8' }}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!listLoading && matches.length === 0 && totalCount > 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="text.secondary">По вашему запросу ничего не найдено</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Pagination size="small" count={Math.ceil(totalCount / 50)} page={page}
                onChange={(_, v) => setPage(v)} color="primary" />
            </Box>
          </Box>
        )}

        {activeTab === 2 && (
          <TableContainer component={Paper} sx={{ borderRadius: 2, border: '1px solid #e0e0e0' }}>
            <Table size="small">
              <TableHead sx={{ bgcolor: '#fafafa' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>AGSK</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>ЕНС ТРУ</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Товар КТП</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>ДВС %</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Действие</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {archive.map(item => (
                  <TableRow key={item.id} hover>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{item.agsk_code}</TableCell>
                    <TableCell>{item.enstru_code}</TableCell>
                    <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <Tooltip title={item.product_name_ktp || '—'}>
                        <Typography variant="body2">{item.product_name_ktp || '—'}</Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.dvc_percent}% ДВС`} size="small" variant="outlined" sx={{ height: 20 }} />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" color="error" onClick={() => removeFromLibrary(item.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* ДИАЛОГ ЗАГРУЗКИ ТЕСТА */}
        <Dialog open={uploadDialogOpen} onClose={() => !uploading && setUploadDialogOpen(false)} maxWidth="xs" fullWidth>
            <DialogTitle sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                <ScienceIcon color="warning" />
                Новый тестовый проект
            </DialogTitle>
            <DialogContent>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                    Тестовый проект создается для личного анализа. Библиотека сопоставлений будет пополняться как обычно.
                </Typography>
                <TextField
                    fullWidth
                    label="Название проекта"
                    placeholder="Напр. Анализ ПСД школы..."
                    value={testProjectName}
                    onChange={(e) => setTestProjectName(e.target.value)}
                    sx={{ mb: 3, mt: 1 }}
                    size="small"
                />
                
                <Button
                    component="label"
                    variant="outlined"
                    fullWidth
                    startIcon={<UploadIcon />}
                    sx={{ py: 2, borderStyle: 'dashed' }}
                >
                    {selectedFile ? selectedFile.name : 'Выбрать файл .kenml / .zip'}
                    <input
                        type="file"
                        hidden
                        accept=".kenml,.zip"
                        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    />
                </Button>
            </DialogContent>
            <DialogActions sx={{ p: 2 }}>
                <Button onClick={() => setUploadDialogOpen(false)} disabled={uploading}>Отмена</Button>
                <Button 
                    variant="contained" 
                    color="warning" 
                    onClick={handleUploadTest}
                    disabled={uploading || !selectedFile || !testProjectName}
                    startIcon={uploading && <CircularProgress size={16} color="inherit" />}
                >
                    {uploading ? 'Загрузка...' : 'Создать'}
                </Button>
            </DialogActions>
        </Dialog>

        <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}
          maxWidth="xl" fullWidth
          PaperProps={{ sx: { height: '85vh', borderRadius: 2, overflow: 'hidden' } }}>

          <DialogTitle sx={{
            borderBottom: '1px solid #eee', py: 1.5, px: 2,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
          }}>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold" color="primary">
                Редактор Библиотеки Замен
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 600, color: 'text.primary', wordBreak: 'break-word' }}>
                АГСК: <span style={{ color: '#1976d2', fontWeight: 800 }}>{editingMatch?.code_sn}</span> — {editingMatch?.name}
              </Typography>
            </Box>
            <IconButton size="small" onClick={() => setEditDialogOpen(false)}>
              <CloseIcon />
            </IconButton>
          </DialogTitle>

          <DialogContent sx={{ p: 0, display: 'flex', bgcolor: '#f8f9fa', overflow: 'hidden', flex: 1 }}>
            {editingMatch && (
              <Box sx={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>

                <Box sx={{
                  width: 320, minWidth: 320, bgcolor: 'white',
                  borderRight: '1px solid #e0e0e0',
                  display: 'flex', flexDirection: 'column', overflow: 'hidden'
                }}>
                  <Box sx={{ p: 1.5, bgcolor: '#f0f7ff', borderBottom: '1px solid #e3f2fd' }}>
                    <Typography variant="caption" fontWeight="bold" color="primary">
                      ТЕКУЩАЯ БИБЛИОТЕКА
                    </Typography>
                  </Box>
                  <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 1.5 }}>
                    {library.length === 0 ? (
                      <Typography variant="caption" color="text.secondary" sx={{ p: 1, display: 'block' }}>
                        Нет добавленных соответствий
                      </Typography>
                    ) : library.map(item => (
                      <Paper key={item.id} elevation={0} sx={{
                        p: 1.5, mb: 1.5, border: '1px solid #e0e0e0',
                        borderRadius: 2, position: 'relative', bgcolor: '#fafafa', width: '100%'
                      }}>
                        <IconButton size="small" sx={{ position: 'absolute', top: 4, right: 4 }}
                          onClick={() => removeFromLibrary(item.id)}>
                          <DeleteIcon sx={{ fontSize: 14 }} color="error" />
                        </IconButton>
                        <Typography variant="caption" fontWeight="bold" color="primary"
                          sx={{ display: 'block', mb: 0.5 }}>
                          {item.enstru_code}
                        </Typography>
                        <Typography sx={{ fontSize: '0.7rem', mb: 1, wordBreak: 'break-word', lineHeight: 1.3 }}>
                          {item.enstru_name_ru}
                        </Typography>
                        {item.product_name_ktp && (
                          <Box sx={{ p: 0.8, bgcolor: '#fffbe6', borderRadius: 1, border: '1px solid #ffe58f', mt: 1 }}>
                            <Typography sx={{ fontSize: '0.65rem', fontWeight: 'bold', wordBreak: 'break-word', mb: 0.5 }}>
                              {item.product_name_ktp}
                            </Typography>
                            <Chip label={`${item.dvc_percent}% ДВС`} size="small"
                              sx={{ height: 18, fontSize: '0.6rem' }} />
                          </Box>
                        )}
                      </Paper>
                    ))}

                    {recommendations.length > 0 && (
                      <Divider sx={{ my: 2 }}>
                        <Typography variant="caption" color="text.secondary">СИСТЕМА СОВЕТУЕТ</Typography>
                      </Divider>
                    )}
                    {recommendations.map((rec, idx) => (
                      <Paper key={`${rec.enstru_code}-${idx}`} elevation={0} sx={{
                        p: 1.5, mb: 1.5, border: '1px dashed #1976d2',
                        borderRadius: 2, bgcolor: '#f0f7ff', width: '100%'
                      }}>
                        <Box sx={{ mb: 1 }}>
                          <Typography sx={{ fontSize: '0.8rem', fontWeight: '800', color: '#1a237e', mb: 0.5, lineHeight: 1.2 }}>
                            <Highlight text={rec.enstru_name} search={reestrSearch} />
                          </Typography>
                          
                          {rec.product && (
                            <Typography sx={{ fontSize: '0.65rem', color: '#455a64', mb: 1, fontStyle: 'italic', wordBreak: 'break-word' }}>
                              <Highlight text={rec.product} search={reestrSearch} />
                            </Typography>
                          )}

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                            <Typography sx={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'primary.main', bgcolor: '#e3f2fd', px: 1, borderRadius: 1 }}>
                              <Highlight text={rec.enstru_code} search={reestrSearch} />
                            </Typography>
                            <Typography sx={{ fontSize: '0.7rem', color: '#1976d2', fontWeight: 'bold' }}>{rec.score}%</Typography>
                          </Box>
                        </Box>

                        {rec.agsk3_codes?.length > 0 && (
                          <AgskChips
                            codes={rec.agsk3_codes}
                            names={rec.agsk3_names}
                            highlight={editingMatch.code_sn}
                          />
                        )}

                        <Button size="small" fullWidth variant="outlined"
                          onClick={() => addToLibrary(rec, 'rec')}
                          sx={{ fontSize: '0.65rem', textTransform: 'none', py: 0.5, mt: 1.5 }}>
                          Добавить в библиотеку
                        </Button>
                      </Paper>
                    ))}
                  </Box>
                </Box>

                <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

                  <Box sx={{ bgcolor: 'white', borderBottom: '1px solid #e0e0e0' }}>
                    <Tabs
                      value={searchMode}
                      onChange={(_, v) => setSearchMode(v as SearchMode)}
                      sx={{ minHeight: 36, px: 1.5 }}
                      TabIndicatorProps={{ style: { height: 2 } }}
                    >
                      {SEARCH_TABS.map(t => (
                        <Tab
                          key={t.mode}
                          value={t.mode}
                          label={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              {t.mode === 'agsk' && <AgskIcon  sx={{ fontSize: 13 }} />}
                              {t.mode === 'name' && <CategoryIcon sx={{ fontSize: 13 }} />}
                              {t.mode === 'all'  && <SearchIcon   sx={{ fontSize: 13 }} />}
                              <span>{t.label}</span>
                            </Box>
                          }
                          sx={{ textTransform: 'none', minHeight: 36, fontSize: '0.75rem', py: 0, px: 1.5 }}
                        />
                      ))}
                    </Tabs>

                    <Box sx={{ px: 1.5, pb: 1.5, pt: 0.5 }}>
                      <TextField
                        fullWidth size="small"
                        placeholder={currentSearchTab.placeholder}
                        value={reestrSearch}
                        onChange={e => setReestrSearch(e.target.value)}
                        autoFocus
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <SearchIcon fontSize="small" />
                            </InputAdornment>
                          ),
                          endAdornment: reestrLoading && <CircularProgress size={16} />,
                        }}
                      />
                      {searchMode === 'agsk' && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                          Введите начало кода — будут найдены все записи с совпадающим префиксом
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {reestrResults.length === 0 && debouncedReestrSearch.length >= 2 && !reestrLoading && (
                      <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'white' }}>
                        <Typography variant="body2" color="text.secondary">Ничего не найдено</Typography>
                      </Paper>
                    )}

                    {reestrResults.length === 0 && debouncedReestrSearch.length === 0 && (
                      <Box sx={{ textAlign: 'center', mt: 4, color: '#b0bec5' }}>
                        <SearchIcon sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="body2">
                          {searchMode === 'agsk'
                            ? 'Введите АГСК-код или его начало (напр. 541-801)'
                            : 'Начните вводить для поиска в реестре КТП'}
                        </Typography>
                      </Box>
                    )}

                    {reestrResults.map(r => (
                      <Card key={`${r.ktp_id}-${r.enstru_code}`} elevation={0} sx={{
                        border: '1px solid #e0e0e0', borderRadius: 2,
                        width: '100%', boxSizing: 'border-box', flexShrink: 0,
                        transition: 'all 0.2s',
                        '&:hover': { borderColor: '#1976d2', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }
                      }}>
                        <CardContent sx={{ p: 2 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5, gap: 1 }}>
                            <Box sx={{ minWidth: 0, flex: 1 }}>
                              <Typography variant="caption" fontWeight="bold" color="primary"
                                sx={{ display: 'block', mb: 0.5 }}>
                                Код: <Highlight text={r.enstru_code} search={debouncedReestrSearch} />
                              </Typography>
                              <Typography variant="body2" fontWeight="bold"
                                sx={{ wordBreak: 'break-word', whiteSpace: 'normal', lineHeight: 1.4 }}>
                                <Highlight text={r.product} search={debouncedReestrSearch} />
                              </Typography>
                            </Box>
                            <Chip
                              label={`${r.dvc_percent}% ДВС`} size="small"
                              color={getDvcColor(r.dvc_percent)}
                              variant={r.dvc_percent === 100 ? 'filled' : 'outlined'}
                              sx={{ height: 24, fontSize: '0.7rem', fontWeight: 'bold', flexShrink: 0 }}
                            />
                          </Box>

                          <Box sx={{ mb: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.75 }}>
                              <BusinessIcon sx={{ fontSize: 14, color: '#64748b', mt: 0.2, flexShrink: 0 }} />
                              <Typography sx={{ fontSize: '0.75rem', color: '#334155', wordBreak: 'break-word', lineHeight: 1.4 }}>
                                <Highlight text={r.company} search={debouncedReestrSearch} />
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75 }}>
                              <BinIcon sx={{ fontSize: 14, color: '#64748b', flexShrink: 0 }} />
                              <Typography sx={{ fontSize: '0.7rem', color: '#475569' }}>
                                БИН: <Highlight text={r.bin} search={debouncedReestrSearch} />
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LocationOnIcon sx={{ fontSize: 14, color: '#64748b', flexShrink: 0 }} />
                              <Typography sx={{ fontSize: '0.7rem', color: '#475569', wordBreak: 'break-word' }}>
                                <Highlight text={r.address} search={debouncedReestrSearch} />
                              </Typography>
                            </Box>
                          </Box>

                          {r.agsk3_codes && r.agsk3_codes.length > 0 && (
                            <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid #f0f0f0' }}>
                              <Typography sx={{ fontSize: '0.65rem', color: '#90a4ae', mb: 0.5, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                АГСК-коды в реестре:
                              </Typography>
                              <AgskChips
                                codes={r.agsk3_codes}
                                names={r.agsk3_names}
                                highlight={
                                  (searchMode === 'agsk' || searchMode === 'all') ? debouncedReestrSearch : editingMatch?.code_sn
                                }
                              />
                            </Box>
                          )}

                          <Button size="small" variant="contained" disableElevation fullWidth
                            onClick={() => addToLibrary(r, 'ktp')}
                            sx={{ textTransform: 'none', fontSize: '0.75rem', mt: 1.5, borderRadius: 1.5, py: 0.75 }}>
                            Добавить
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                </Box>
              </Box>
            )}
          </DialogContent>

          <DialogActions sx={{ px: 2, py: 1, borderTop: '1px solid #e0e0e0' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <AutoIcon sx={{ fontSize: 16, color: '#64748b' }} />
              <Typography sx={{ fontSize: '0.65rem', color: '#64748b' }}>
                Применяется вариант с минимальным ДВС
              </Typography>
            </Box>
            <Button size="small" onClick={() => setEditDialogOpen(false)} variant="contained"
              sx={{ textTransform: 'none', fontWeight: 'bold' }}>
              Готово
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Box>
  );
};

export default PsdAnalystPage;
