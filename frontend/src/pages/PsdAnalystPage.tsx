import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Button, Tabs, Tab, Chip, IconButton, Dialog,
  DialogTitle, DialogContent, TextField, DialogActions, Alert, Tooltip,
  Pagination, Grid, Divider, Card, CardContent, InputAdornment, List,
  ListItem, ListItemText, LinearProgress, CircularProgress, Stack
} from '@mui/material';
import {
  Add as AddIcon, Delete as DeleteIcon, Download as DownloadIcon,
  Search as SearchIcon, Refresh as RefreshIcon, Business as BusinessIcon,
  CheckCircle as CheckCircleIcon, Factory as FactoryIcon, Close as CloseIcon,
  Inventory as InventoryIcon, LibraryBooks as LibraryIcon, PlayArrow as PlayIcon,
  Edit as EditIcon, History as HistoryIcon, LocationOn as LocationOnIcon,
  CalendarToday as CalendarTodayIcon, Fingerprint as BinIcon, AutoAwesome as AutoIcon
} from '@mui/icons-material';
import { useTranslation } from '../i18n';
import Header from '../components/Header';
import api from '../services/api';

// Hook for debouncing
function useDebounce(value: any, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

interface AgskMatch {
  item_id: number;
  position_number: string;
  name: string;
  code_sn: string;
  unit: string;
  volume: number;
  enstru_code?: string;
  enstru_name?: string;
  match_type: 'auto' | 'manual' | 'auto_ktp' | 'none';
  match_score?: number;
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
}

const PsdAnalystPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(0);
  const [documents, setDocuments] = useState<any[]>([]);
  const [matches, setMatches] = useState<AgskMatch[]>([]);
  const [archive, setArchive] = useState<LibraryItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [parsing, setParsing] = useState(false);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingMatch, setEditingMatch] = useState<AgskMatch | null>(null);
  const [library, setLibrary] = useState<LibraryItem[]>([]);
  const [reestrResults, setReestrResults] = useState<ReestrResult[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);

  const [reestrSearch, setReestrSearch] = useState('');
  const [agskSearch, setAgskSearch] = useState('');
  const [reestrLoading, setReestrLoading] = useState(false);

  const debouncedReestrSearch = useDebounce(reestrSearch, 500);
  const debouncedAgskSearch = useDebounce(agskSearch, 500);

  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [onlyUnmatched, setOnlyUnmatched] = useState(false);

  useEffect(() => {
    loadDocuments();
    loadArchive();
  }, []);

  useEffect(() => {
    if (selectedDoc) {
      loadMatches(selectedDoc.id);
    }
  }, [selectedDoc, onlyUnmatched, page, debouncedAgskSearch]);

  useEffect(() => {
    if (debouncedReestrSearch.length >= 2) {
      handleSearchReestr();
    }
  }, [debouncedReestrSearch]);

  const loadDocuments = async () => {
    const res = await api.get('/psd-analyst/documents');
    setDocuments(res.data);
  };

  const loadArchive = async () => {
    const res = await api.get('/psd-analyst/existing-matches');
    setArchive(res.data);
  };

  const loadMatches = async (docId: number) => {
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
      setMatches(res.data.items);
      setTotalCount(res.data.total);
    } finally {
      setListLoading(false);
    }
  };

  const handleParse = async () => {
    if (!selectedDoc) return;
    setParsing(true);
    try {
      await api.post(`/psd-analyst/documents/${selectedDoc.id}/parse`);
      await loadMatches(selectedDoc.id);
    } finally {
      setParsing(false);
    }
  };

  const openEditDialog = async (match: AgskMatch) => {
    setEditingMatch(match);
    setEditDialogOpen(true);
    setReestrSearch('');
    setReestrResults([]);
    const libRes = await api.get(`/psd-analyst/agsk-library/${match.code_sn}`);
    setLibrary(libRes.data);
    const recRes = await api.get('/psd-analyst/suggest-enstru-for-agsk', {
      params: { agsk_code: match.code_sn }
    });
    setRecommendations(recRes.data);
  };

  const handleSearchReestr = async () => {
    setReestrLoading(true);
    try {
      const res = await api.get('/psd-analyst/search-enstru-reestr', {
        params: { query: debouncedReestrSearch }
      });
      setReestrResults(res.data);
    } finally {
      setReestrLoading(false);
    }
  };

  const addToLibrary = async (item: any, type: 'rec' | 'ktp') => {
    if (!editingMatch) return;
    await api.post('/psd-analyst/manual-match', {
      agsk_code: editingMatch.code_sn,
      enstru_code: item.enstru_code,
      ktp_id: item.ktp_id || null,
      dvc_percent: item.dvc_percent || 0,
      product_name_ktp: item.product || null,
      doc_id: selectedDoc?.id
    });
    const libRes = await api.get(`/psd-analyst/agsk-library/${editingMatch.code_sn}`);
    setLibrary(libRes.data);
    loadArchive();
  };

  const removeFromLibrary = async (id: number) => {
    await api.delete(`/psd-analyst/agsk-library/${id}`);
    if (editingMatch) {
      const libRes = await api.get(`/psd-analyst/agsk-library/${editingMatch.code_sn}`);
      setLibrary(libRes.data);
    }
    loadArchive();
  };

  const handleExportExcel = (format: string) => {
    api.get('/psd-analyst/export-matches', {
      params: { format_type: format },
      responseType: 'blob'
    }).then(r => {
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `library_${format}.xlsx`);
      document.body.appendChild(link);
      link.click();
    });
  };

  const getMatchTypeStyles = (type: string) => {
    switch (type) {
      case 'manual':
        return { label: 'Библиотека', color: 'success' };
      case 'auto':
        return { label: 'Авто', color: 'info' };
      case 'auto_ktp':
        return { label: 'КТП', color: 'warning' };
      default:
        return { label: 'Нет', color: 'error' };
    }
  };

  const getDvcColor = (percent: number) => {
    if (percent === 100) return 'success';
    if (percent >= 70) return 'warning';
    return 'default';
  };

  return (
    <Box sx={{ bgcolor: '#f5f7f9', minHeight: '100vh' }}>
      <Header />
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" fontWeight="bold" color="#1a237e">
            Аналитика ПСД
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadDocuments}
              sx={{ bgcolor: 'white', textTransform: 'none' }}
            >
              Обновить
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={() => handleExportExcel('full')}
              sx={{ textTransform: 'none' }}
            >
              Экспорт
            </Button>
          </Stack>
        </Box>

        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v)}
          sx={{ mb: 2, bgcolor: 'white', borderRadius: 2, minHeight: 40 }}
        >
          <Tab label="Документы" sx={{ textTransform: 'none', minHeight: 40 }} />
          <Tab
            label="Рабочая область"
            disabled={!selectedDoc}
            sx={{ textTransform: 'none', minHeight: 40 }}
          />
          <Tab label="Архив" sx={{ textTransform: 'none', minHeight: 40 }} />
        </Tabs>

        {activeTab === 0 && (
          <TableContainer
            component={Paper}
            elevation={0}
            sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}
          >
            <Table size="small">
              <TableHead sx={{ bgcolor: '#fafafa' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Заказчик</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Дата</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Статус</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                    Действие
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id} hover>
                    <TableCell>#{doc.id}</TableCell>
                    <TableCell>{doc.bank_name}</TableCell>
                    <TableCell>
                      {new Date(doc.received_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Chip label={doc.status} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      {!doc.assigned_to ? (
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => api
                            .post(`/psd-analyst/documents/${doc.id}/assign`)
                            .then(loadDocuments)
                          }
                        >
                          Взять
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setSelectedDoc(doc);
                            setActiveTab(1);
                          }}
                        >
                          Открыть
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {activeTab === 1 && selectedDoc && (
          <Box>
            <Paper sx={{
              p: 1.5,
              mb: 2,
              display: 'flex',
              gap: 2,
              alignItems: 'center',
              borderRadius: 2,
              flexWrap: 'wrap'
            }}>
              <Typography variant="subtitle2" fontWeight="bold">
                #{selectedDoc.id} {selectedDoc.bank_name}
              </Typography>
              <Divider orientation="vertical" flexItem />
              {totalCount === 0 ? (
                <Button
                  size="small"
                  variant="contained"
                  color="warning"
                  onClick={handleParse}
                  disabled={parsing}
                >
                  {parsing ? 'Загрузка...' : 'Распарсить'}
                </Button>
              ) : (
                <>
                  <TextField
                    size="small"
                    placeholder="Поиск..."
                    value={agskSearch}
                    onChange={(e) => setAgskSearch(e.target.value)}
                    sx={{ width: 250 }}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <SearchIcon fontSize="small" />
                        </InputAdornment>
                      )
                    }}
                  />
                  <Button
                    size="small"
                    variant={onlyUnmatched ? "contained" : "outlined"}
                    color="error"
                    onClick={() => setOnlyUnmatched(!onlyUnmatched)}
                  >
                    Несопоставленные
                  </Button>
                </>
              )}
            </Paper>

            {totalCount > 0 && (
              <TableContainer
                component={Paper}
                sx={{
                  borderRadius: 2,
                  border: '1px solid #e0e0e0',
                  position: 'relative'
                }}
              >
                {listLoading && (
                  <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0 }} />
                )}
                <Table size="small">
                  <TableHead sx={{ bgcolor: '#fafafa' }}>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold' }}>№</TableCell>
                      <TableCell sx={{ fontWeight: 'bold' }}>Наименование</TableCell>
                      <TableCell sx={{ fontWeight: 'bold' }}>AGSK</TableCell>
                      <TableCell sx={{ fontWeight: 'bold' }}>ЕНС ТРУ</TableCell>
                      <TableCell sx={{ fontWeight: 'bold' }}>Тип</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                        Действие
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {matches.map((m) => (
                      <TableRow key={m.item_id} hover>
                        <TableCell>{m.position_number}</TableCell>
                        <TableCell sx={{
                          maxWidth: 300,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          <Tooltip title={m.name}>
                            <Typography variant="body2">{m.name}</Typography>
                          </Tooltip>
                        </TableCell>
                        <TableCell sx={{
                          fontFamily: 'monospace',
                          fontSize: '0.8rem'
                        }}>
                          {m.code_sn}
                        </TableCell>
                        <TableCell sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                          {m.enstru_code || '—'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getMatchTypeStyles(m.match_type).label}
                            color={getMatchTypeStyles(m.match_type).color as any}
                            size="small"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            onClick={() => openEditDialog(m)}
                            sx={{ bgcolor: '#f0f4f8' }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Pagination
                size="small"
                count={Math.ceil(totalCount / 50)}
                page={page}
                onChange={(_, v) => setPage(v)}
                color="primary"
              />
            </Box>
          </Box>
        )}

        {activeTab === 2 && (
          <TableContainer
            component={Paper}
            sx={{ borderRadius: 2, border: '1px solid #e0e0e0' }}
          >
            <Table size="small">
              <TableHead sx={{ bgcolor: '#fafafa' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>AGSK</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>ЕНС ТРУ</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Товар КТП</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>ДВС %</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                    Действие
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {archive.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell sx={{ fontFamily: 'monospace' }}>
                      {item.agsk_code}
                    </TableCell>
                    <TableCell>{item.enstru_code}</TableCell>
                    <TableCell sx={{
                      maxWidth: 300,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      <Tooltip title={item.product_name_ktp || '—'}>
                        <Typography variant="body2">
                          {item.product_name_ktp || '—'}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${item.dvc_percent}%`}
                        size="small"
                        variant="outlined"
                        sx={{ height: 20 }}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => removeFromLibrary(item.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* DIALOG FOR MATCHING */}
        <Dialog
          open={editDialogOpen}
          onClose={() => setEditDialogOpen(false)}
          maxWidth="xl"
          fullWidth
          PaperProps={{ sx: { height: '85vh', borderRadius: 2, overflow: 'hidden' } }}
        >
          <DialogTitle sx={{
            borderBottom: '1px solid #eee',
            py: 1.5,
            px: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                Редактор Библиотеки Замен
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                АГСК: <b>{editingMatch?.code_sn}</b> | {editingMatch?.name}
              </Typography>
            </Box>
            <IconButton size="small" onClick={() => setEditDialogOpen(false)}>
              <CloseIcon />
            </IconButton>
          </DialogTitle>

          <DialogContent sx={{
            p: 0,
            display: 'flex',
            bgcolor: '#f8f9fa',
            overflow: 'hidden',
            flex: 1
          }}>
            {editingMatch && (
              <Box sx={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>

                {/* LEFT PANEL - LIBRARY & RECOMMENDATIONS */}
                <Box sx={{
                  width: 320,
                  minWidth: 320,
                  bgcolor: 'white',
                  borderRight: '1px solid #e0e0e0',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden'
                }}>
                  <Box sx={{
                    p: 1.5,
                    bgcolor: '#f0f7ff',
                    borderBottom: '1px solid #e3f2fd'
                  }}>
                    <Typography variant="caption" fontWeight="bold" color="primary">
                      ТЕКУЩАЯ БИБЛИОТЕКА
                    </Typography>
                  </Box>
                  <Box sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    p: 1.5
                  }}>
                    {library.length === 0 ? (
                      <Typography variant="caption" color="text.secondary" sx={{ p: 1, display: 'block' }}>
                        Нет добавленных соответствий
                      </Typography>
                    ) : (
                      library.map(item => (
                        <Paper
                          key={item.id}
                          elevation={0}
                          sx={{
                            p: 1.5,
                            mb: 1.5,
                            border: '1px solid #e0e0e0',
                            borderRadius: 2,
                            position: 'relative',
                            bgcolor: '#fafafa',
                            width: '100%'
                          }}
                        >
                          <IconButton
                            size="small"
                            sx={{ position: 'absolute', top: 4, right: 4 }}
                            onClick={() => removeFromLibrary(item.id)}
                          >
                            <DeleteIcon sx={{ fontSize: 14 }} color="error" />
                          </IconButton>
                          <Typography variant="caption" fontWeight="bold" color="primary" sx={{ display: 'block', mb: 0.5 }}>
                            {item.enstru_code}
                          </Typography>
                          <Typography sx={{
                            fontSize: '0.7rem',
                            mb: 1,
                            wordBreak: 'break-word',
                            lineHeight: 1.3
                          }}>
                            {item.enstru_name_ru}
                          </Typography>
                          {item.product_name_ktp && (
                            <Box sx={{
                              p: 0.8,
                              bgcolor: '#fffbe6',
                              borderRadius: 1,
                              border: '1px solid #ffe58f',
                              mt: 1
                            }}>
                              <Typography sx={{
                                fontSize: '0.65rem',
                                fontWeight: 'bold',
                                wordBreak: 'break-word',
                                mb: 0.5
                              }}>
                                {item.product_name_ktp}
                              </Typography>
                              <Chip
                                label={`${item.dvc_percent}% ДВС`}
                                size="small"
                                sx={{ height: 18, fontSize: '0.6rem' }}
                              />
                            </Box>
                          )}
                        </Paper>
                      ))
                    )}

                    {recommendations.length > 0 && (
                      <Divider sx={{ my: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                          СИСТЕМА СОВЕТУЕТ
                        </Typography>
                      </Divider>
                    )}
                    {recommendations.map((rec, idx) => (
                      <Paper
                        key={`${rec.enstru_code}-${idx}`}
                        elevation={0}
                        sx={{
                          p: 1.5,
                          mb: 1.5,
                          border: '1px dashed #1976d2',
                          borderRadius: 2,
                          bgcolor: '#f0f7ff',
                          width: '100%'
                        }}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>
                            {rec.enstru_code}
                          </Typography>
                          <Typography sx={{ fontSize: '0.7rem', color: '#1976d2' }}>
                            {rec.score}%
                          </Typography>
                        </Box>
                        <Typography sx={{
                          fontSize: '0.65rem',
                          color: '#1e3a8a',
                          mb: 1,
                          wordBreak: 'break-word',
                          lineHeight: 1.3
                        }}>
                          {rec.enstru_name}
                        </Typography>
                        <Button
                          size="small"
                          fullWidth
                          variant="outlined"
                          onClick={() => addToLibrary(rec, 'rec')}
                          sx={{ fontSize: '0.65rem', textTransform: 'none', py: 0.5 }}
                        >
                          Добавить в библиотеку
                        </Button>
                      </Paper>
                    ))}
                  </Box>
                </Box>

                {/* RIGHT PANEL - REGISTRY SEARCH */}
                {/* ───────────────────────────────────────────────────────────────
                    ИСПРАВЛЕНИЕ: убрали Grid, используем flex-колонку.
                    Это гарантирует что каждая карточка занимает 100% ширины
                    правой панели без лишних отступов от MUI Grid-системы.
                ─────────────────────────────────────────────────────────────── */}
                <Box sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                  minWidth: 0
                }}>
                  {/* Search bar */}
                  <Box sx={{ p: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: 'white' }}>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="Поиск в Реестре КТП (БИН, Название, Продукт)..."
                      value={reestrSearch}
                      onChange={e => setReestrSearch(e.target.value)}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon fontSize="small" />
                          </InputAdornment>
                        ),
                        endAdornment: reestrLoading && <CircularProgress size={16} />
                      }}
                    />
                  </Box>

                  {/* Cards list — flex column, каждая карточка на полную ширину */}
                  <Box sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    p: 2,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 2
                  }}>
                    {/* Пустое состояние */}
                    {reestrResults.length === 0 && debouncedReestrSearch.length >= 2 && !reestrLoading && (
                      <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'white' }}>
                        <Typography variant="body2" color="text.secondary">
                          Ничего не найдено
                        </Typography>
                      </Paper>
                    )}

                    {/* Карточки результатов */}
                    {reestrResults.map(r => (
                      <Card
                        key={`${r.ktp_id}-${r.enstru_code}`}
                        elevation={0}
                        sx={{
                          border: '1px solid #e0e0e0',
                          borderRadius: 2,
                          width: '100%',        // ← явная 100% ширина
                          boxSizing: 'border-box',
                          flexShrink: 0,        // не сжиматься
                          transition: 'all 0.2s',
                          '&:hover': {
                            borderColor: '#1976d2',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                          }
                        }}
                      >
                        <CardContent sx={{ p: 2 }}>
                          {/* Заголовок: код + ДВС */}
                          <Box sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'flex-start',
                            mb: 1.5,
                            gap: 1
                          }}>
                            <Box sx={{ minWidth: 0, flex: 1 }}>
                              <Typography
                                variant="caption"
                                fontWeight="bold"
                                color="primary"
                                sx={{ display: 'block', mb: 0.5 }}
                              >
                                Код: {r.enstru_code}
                              </Typography>
                              <Typography
                                variant="body2"
                                fontWeight="bold"
                                sx={{
                                  wordBreak: 'break-word',
                                  whiteSpace: 'normal',
                                  lineHeight: 1.4
                                }}
                              >
                                {r.product}
                              </Typography>
                            </Box>
                            <Chip
                              label={`${r.dvc_percent}% ДВС`}
                              size="small"
                              color={getDvcColor(r.dvc_percent)}
                              variant={r.dvc_percent === 100 ? 'filled' : 'outlined'}
                              sx={{
                                height: 24,
                                fontSize: '0.7rem',
                                fontWeight: 'bold',
                                flexShrink: 0
                              }}
                            />
                          </Box>

                          {/* Компания и детали */}
                          <Box sx={{ mb: 1.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                              <BusinessIcon sx={{ fontSize: 14, color: '#64748b', mt: 0.2, flexShrink: 0 }} />
                              <Typography
                                sx={{
                                  fontSize: '0.75rem',
                                  color: '#334155',
                                  wordBreak: 'break-word',
                                  whiteSpace: 'normal',
                                  lineHeight: 1.4
                                }}
                              >
                                {r.company}
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <BinIcon sx={{ fontSize: 14, color: '#64748b', flexShrink: 0 }} />
                              <Typography sx={{ fontSize: '0.7rem', color: '#475569' }}>
                                БИН: {r.bin}
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LocationOnIcon sx={{ fontSize: 14, color: '#64748b', flexShrink: 0 }} />
                              <Typography sx={{ fontSize: '0.7rem', color: '#475569', wordBreak: 'break-word' }}>
                                {r.address}
                              </Typography>
                            </Box>
                          </Box>

                          {/* Кнопка */}
                          <Button
                            size="small"
                            variant="contained"
                            disableElevation
                            fullWidth
                            onClick={() => addToLibrary(r, 'ktp')}
                            sx={{
                              textTransform: 'none',
                              fontSize: '0.75rem',
                              mt: 1,
                              borderRadius: 1.5,
                              py: 0.75
                            }}
                          >
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
            <Button
              size="small"
              onClick={() => setEditDialogOpen(false)}
              variant="contained"
              sx={{ textTransform: 'none', fontWeight: 'bold' }}
            >
              Готово
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Box>
  );
};

export default PsdAnalystPage;