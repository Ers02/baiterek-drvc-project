import React, { useState, useEffect, useRef } from 'react';
import {
  Box, Container, Typography, Paper, Tabs, Tab, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  CircularProgress, Alert, Chip, Stack, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, IconButton, Tooltip, Grid, Card, CardContent
} from '@mui/material';
import { 
    Upload as UploadIcon, Person as PersonIcon, Description as DescriptionIcon, 
    Analytics as AnalyticsIcon, Inbox as InboxIcon, Download as DownloadIcon,
    Send as SendIcon, CheckCircle as CheckCircleIcon, Error as ErrorIcon,
    AccessTime as AccessTimeIcon, InsertChart as InsertChartIcon,
    MonetizationOn as MonetizationOnIcon, PieChart as PieChartIcon,
    ListAlt as ListAltIcon, Category as CategoryIcon
} from '@mui/icons-material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement, // Needed for Pie charts
} from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import Header from '../components/Header';
import { differenceInDays } from 'date-fns';
import {
    adminGetUsers,
    adminGetPlans,
    adminAnalyzePsd,
    getAdminTaskStatus,
    downloadAdminTaskResult,
    getExternalDocs,
    uploadExternalDoc,
    sendExternalResponse,
    downloadExternalSource,
    uploadEstimateTemplate,
    getEstimateAnalysis,
} from '../services/api';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement // Register ArcElement for Pie charts
);

const UsersTab = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    adminGetUsers()
      .then(setUsers)
      .catch(() => setError("Не удалось загрузить пользователей."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>ИИН</TableCell>
            <TableCell>ФИО</TableCell>
            <TableCell>Организация</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Активен</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell>{user.id}</TableCell>
              <TableCell>{user.iin}</TableCell>
              <TableCell>{user.full_name}</TableCell>
              <TableCell>{user.org_name}</TableCell>
              <TableCell>{user.email}</TableCell>
              <TableCell>
                <Chip label={user.is_active ? "Да" : "Нет"} color={user.is_active ? "success" : "default"} size="small" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const PlansTab = () => {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    adminGetPlans()
      .then(setPlans)
      .catch(() => setError("Не удалось загрузить планы."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Название</TableCell>
            <TableCell>Год</TableCell>
            <TableCell>Создан</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {plans.map((plan) => (
            <TableRow key={plan.id}>
              <TableCell>{plan.id}</TableCell>
              <TableCell>{plan.plan_name}</TableCell>
              <TableCell>{plan.year}</TableCell>
              <TableCell>{new Date(plan.created_at).toLocaleDateString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const AnalyticsTab = () => {
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [message, setMessage] = useState<string>('');

  const isDownloading = useRef(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;
    
    const file = event.target.files[0];
    setError('');
    isDownloading.current = false;

    try {
      const response = await adminAnalyzePsd(file);
      setTaskId(response.task_id);
      setStatus('pending');
      setMessage(response.message);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ошибка запуска анализа");
    } finally {
      event.target.value = '';
    }
  };

  useEffect(() => {
    if (!taskId) return;

    const interval = setInterval(async () => {
        if (isDownloading.current) return;

        try {
            const statusData = await getAdminTaskStatus(taskId);
            setStatus(statusData.status);
            setMessage(statusData.message);

            if (statusData.status === 'completed') {
                clearInterval(interval);
                isDownloading.current = true;

                try {
                    await downloadAdminTaskResult(taskId);
                } catch (e) {
                    console.error("Download error:", e);
                    setError("Ошибка скачивания файла");
                } finally {
                    setTaskId(null);
                    setStatus('');
                    setMessage('');
                    isDownloading.current = false;
                }
            } else if (statusData.status === 'error') {
                clearInterval(interval);
                setError(`Ошибка анализа: ${statusData.error}`);
                setTaskId(null);
            }
        } catch (e) {
            console.error("Error polling task status", e);
            clearInterval(interval);
            setTaskId(null);
            setError("Ошибка связи с сервером");
        }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId]);

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="contained"
          component="label"
          startIcon={<UploadIcon />}
          disabled={!!taskId}
        >
          {taskId ? "Анализ..." : "Загрузить ПСД (KENML/ZIP)"}
          <input type="file" hidden accept=".kenml,.xml,.zip" onChange={handleFileUpload} />
        </Button>
        <Typography variant="body2" color="text.secondary">
            Загрузите файл для поиска поставщиков и генерации отчета.
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Dialog open={!!taskId} disableEscapeKeyDown>
        <DialogTitle>Анализ ПСД</DialogTitle>
        <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 300, py: 2 }}>
                <CircularProgress sx={{ mb: 2 }} />
                <Typography variant="body1" gutterBottom align="center">{message}</Typography>
                <Typography variant="caption" color="text.secondary">Пожалуйста, подождите...</Typography>
            </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

const ExternalDocsTab = () => {
    const [docs, setDocs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [error, setError] = useState('');
    
    const [file, setFile] = useState<File | null>(null);
    const [docType, setDocType] = useState('PSD');
    const [bankName, setBankName] = useState('');
    const [receivedAt, setReceivedAt] = useState('');
    const [notes, setNotes] = useState('');

    const loadDocs = () => {
        setLoading(true);
        setError('');
        getExternalDocs()
            .then(setDocs)
            .catch(() => setError("Не удалось загрузить документы."))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadDocs();
    }, []);

    const handleUpload = async () => {
        if (!file || !bankName || !receivedAt) return;
        try {
            await uploadExternalDoc(file, docType, bankName, receivedAt, notes);
            setUploadOpen(false);
            loadDocs();
            setFile(null);
            setBankName('');
            setReceivedAt('');
            setNotes('');
        } catch (e) {
            alert("Ошибка загрузки");
        }
    };

    const handleSendResponse = async (docId: number) => {
        if (window.confirm("Подтвердить отправку ответа? Статус изменится на 'Отправлен'.")) {
            try {
                await sendExternalResponse(docId);
                loadDocs();
            } catch (e) {
                alert("Ошибка отправки ответа");
            }
        }
    };

    const getDaysInWork = (doc: any) => {
        const start = new Date(doc.received_at);
        const end = doc.completed_at ? new Date(doc.completed_at) : new Date();
        return differenceInDays(end, start);
    };

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            <Box sx={{ mb: 3 }}>
                <Button variant="contained" startIcon={<UploadIcon />} onClick={() => setUploadOpen(true)}>
                    Загрузить документ
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Банк</TableCell>
                            <TableCell>Тип</TableCell>
                            <TableCell>Дата получения</TableCell>
                            <TableCell>Дней в работе</TableCell>
                            <TableCell>Статус</TableCell>
                            <TableCell>Примечание</TableCell>
                            <TableCell align="right">Действия</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {docs.map((doc) => {
                            const days = getDaysInWork(doc);
                            const isOverdue = days > 5 && doc.status !== 'SENT';
                            
                            return (
                                <TableRow key={doc.id}>
                                    <TableCell>{doc.id}</TableCell>
                                    <TableCell>{doc.bank_name}</TableCell>
                                    <TableCell>
                                        <Chip 
                                            label={doc.doc_type} 
                                            color={doc.doc_type === 'PSD' ? 'primary' : 'secondary'} 
                                            size="small" 
                                        />
                                    </TableCell>
                                    <TableCell>{new Date(doc.received_at).toLocaleString()}</TableCell>
                                    <TableCell>
                                        <Chip 
                                            icon={<AccessTimeIcon />}
                                            label={`${days} дн.`} 
                                            color={isOverdue ? 'error' : 'default'} 
                                            variant={isOverdue ? 'filled' : 'outlined'}
                                            size="small" 
                                        />
                                    </TableCell>
                                    <TableCell>
                                        <Chip 
                                            label={doc.status === 'SENT' ? 'Отправлен' : doc.status} 
                                            color={
                                                doc.status === 'SENT' ? 'success' : 
                                                doc.status === 'NEW' ? 'info' : 'default'
                                            } 
                                            size="small" 
                                        />
                                    </TableCell>
                                    <TableCell>{doc.notes}</TableCell>
                                    <TableCell align="right">
                                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                                            <Tooltip title="Скачать файл">
                                                <IconButton size="small" onClick={() => downloadExternalSource(doc.id, doc.file_path.split('/').pop())}>
                                                    <DownloadIcon />
                                                </IconButton>
                                            </Tooltip>
                                            
                                            {doc.status !== 'SENT' && (
                                                <Tooltip title="Отправить ответ">
                                                    <IconButton size="small" color="primary" onClick={() => handleSendResponse(doc.id)}>
                                                        <SendIcon />
                                                    </IconButton>
                                                </Tooltip>
                                            )}
                                            
                                            {doc.status === 'SENT' && (
                                                <Tooltip title="Ответ отправлен">
                                                    <CheckCircleIcon color="success" fontSize="small" />
                                                </Tooltip>
                                            )}
                                        </Stack>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={uploadOpen} onClose={() => setUploadOpen(false)}>
                <DialogTitle>Загрузка внешнего документа</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1, minWidth: 400 }}>
                        <TextField select label="Тип документа" value={docType} onChange={(e) => setDocType(e.target.value)} fullWidth>
                            <MenuItem value="PSD">ПСД (KENML)</MenuItem>
                            <MenuItem value="SMETA">Смета (Excel)</MenuItem>
                        </TextField>
                        <TextField label="Название банка" value={bankName} onChange={(e) => setBankName(e.target.value)} fullWidth />
                        <TextField label="Дата и время получения" type="datetime-local" value={receivedAt} onChange={(e) => setReceivedAt(e.target.value)} fullWidth InputLabelProps={{ shrink: true }} />
                        <TextField label="Примечание" value={notes} onChange={(e) => setNotes(e.target.value)} fullWidth multiline rows={2} />
                        <Button variant="outlined" component="label">
                            {file ? file.name : "Выбрать файл"}
                            <input type="file" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
                        </Button>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setUploadOpen(false)}>Отмена</Button>
                    <Button onClick={handleUpload} variant="contained" disabled={!file || !bankName || !receivedAt}>Загрузить</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

const SummaryCard = ({ title, value, icon }: { title: string, value: string | number, icon: React.ReactElement }) => (
    <Card sx={{ display: 'flex', alignItems: 'center', p: 2 }}>
        <Box sx={{ mr: 2, color: 'primary.main' }}>{icon}</Box>
        <Box>
            <Typography variant="h6" fontWeight="bold">{value}</Typography>
            <Typography variant="body2" color="text.secondary">{title}</Typography>
        </Box>
    </Card>
);

const EstimateTemplateTab = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadMessage, setUploadMessage] = useState('');
    const [uploadError, setUploadError] = useState('');
    const [analysisData, setAnalysisData] = useState<any>(null);
    const [analysisLoading, setAnalysisLoading] = useState(false);
    const [analysisError, setAnalysisError] = useState('');

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (!event.target.files || event.target.files.length === 0) return;
        setFile(event.target.files[0]);
        setUploadMessage('');
        setUploadError('');
    };

    const handleUploadButtonClick = async () => {
        if (!file) {
            setUploadError("Пожалуйста, выберите файл для загрузки.");
            return;
        }
        setUploading(true);
        setUploadMessage('');
        setUploadError('');
        try {
            const response = await uploadEstimateTemplate(file);
            setUploadMessage(response.message);
            setFile(null);
        } catch (e: any) {
            setUploadError(e.response?.data?.detail || "Ошибка загрузки шаблона.");
        } finally {
            setUploading(false);
        }
    };

    const handleAnalyzeButtonClick = async () => {
        setAnalysisLoading(true);
        setAnalysisError('');
        setAnalysisData(null);
        try {
            const data = await getEstimateAnalysis();
            setAnalysisData(data);
        } catch (e: any) {
            setAnalysisError(e.response?.data?.detail || "Ошибка получения данных для анализа.");
        } finally {
            setAnalysisLoading(false);
        }
    };

    return (
        <Box>
            <Typography variant="h6" gutterBottom>Загрузка шаблона сметы</Typography>
            <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
                <Button variant="contained" component="label" startIcon={<UploadIcon />} disabled={uploading}>
                    {file ? file.name : "Выбрать файл сметы (Excel)"}
                    <input type="file" hidden accept=".xlsx,.xls" onChange={handleFileUpload} />
                </Button>
                <Button variant="contained" onClick={handleUploadButtonClick} disabled={!file || uploading}>
                    {uploading ? <CircularProgress size={24} /> : "Загрузить"}
                </Button>
            </Box>
            {uploadMessage && <Alert severity="success" sx={{ mb: 2 }}>{uploadMessage}</Alert>}
            {uploadError && <Alert severity="error" sx={{ mb: 2 }}>{uploadError}</Alert>}

            <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>Анализ сметы</Typography>
            <Box sx={{ mb: 3 }}>
                <Button variant="contained" startIcon={<InsertChartIcon />} onClick={handleAnalyzeButtonClick} disabled={analysisLoading}>
                    {analysisLoading ? <CircularProgress size={24} /> : "Показать анализ"}
                </Button>
            </Box>

            {analysisLoading && <CircularProgress />}
            {analysisError && <Alert severity="error" sx={{ mb: 2 }}>{analysisError}</Alert>}
            
            {analysisData && (
                <Box>
                    <Grid container spacing={3} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={6} md={3}>
                            <SummaryCard title="Общая сумма" value={analysisData.summary.totalAmount} icon={<MonetizationOnIcon fontSize="large" />} />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <SummaryCard title="Кол-во позиций" value={analysisData.summary.itemCount} icon={<ListAltIcon fontSize="large" />} />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <SummaryCard title="Доля ВЦ" value={analysisData.summary.localContentPercentage} icon={<PieChartIcon fontSize="large" />} />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <SummaryCard title="Статей затрат" value={analysisData.summary.uniqueCategories} icon={<CategoryIcon fontSize="large" />} />
                        </Grid>
                    </Grid>

                    <Grid container spacing={4}>
                        <Grid item xs={12} md={6}>
                            <Paper elevation={3} sx={{ p: 2, height: '100%' }}>
                                <Typography variant="h6" gutterBottom>Топ-10 Статей Затрат</Typography>
                                <Box sx={{ height: 400 }}>
                                    <Bar options={{ indexAxis: 'y', responsive: true, maintainAspectRatio: false }} data={analysisData.costItemAnalysis.chartData} />
                                </Box>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Grid container spacing={3}>
                                <Grid item xs={12} sm={6}>
                                    <Paper elevation={3} sx={{ p: 2 }}>
                                        <Typography variant="h6" align="center" gutterBottom>Доля ВЦ</Typography>
                                        <Pie data={analysisData.localContentAnalysis.chartData} />
                                    </Paper>
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <Paper elevation={3} sx={{ p: 2 }}>
                                        <Typography variant="h6" align="center" gutterBottom>Источники</Typography>
                                        <Pie data={analysisData.fundingSourceAnalysis.chartData} />
                                    </Paper>
                                </Grid>
                            </Grid>
                        </Grid>
                    </Grid>
                </Box>
            )}
        </Box>
    );
};


export default function AdminPage() {
  const [tab, setTab] = useState(0);

  return (
    <>
      <Header />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight="bold" sx={{ mb: 4 }}>
          Панель Администратора
        </Typography>

        <Paper sx={{ mb: 3 }}>
          <Tabs value={tab} onChange={(e, v) => setTab(v)} centered>
            <Tab icon={<InboxIcon />} label="Входящие документы" />
            <Tab icon={<AnalyticsIcon />} label="Аналитика ПСД (Ручная)" />
            <Tab icon={<InsertChartIcon />} label="Анализ Сметы" />
            <Tab icon={<PersonIcon />} label="Пользователи" />
            <Tab icon={<DescriptionIcon />} label="Все планы" />
          </Tabs>
        </Paper>

        <Box sx={{ mt: 2 }}>
          {tab === 0 && <ExternalDocsTab />}
          {tab === 1 && <AnalyticsTab />}
          {tab === 2 && <EstimateTemplateTab />}
          {tab === 3 && <UsersTab />}
          {tab === 4 && <PlansTab />}
        </Box>
      </Container>
    </>
  );
}
