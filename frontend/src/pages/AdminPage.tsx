import { useState, useEffect } from 'react';
import {
  Box, Container, Typography, Paper, Tabs, Tab, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  CircularProgress, Alert, Chip, Stack, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, IconButton, Tooltip, Grid, Divider
} from '@mui/material';
import {
    Upload as UploadIcon, Person as PersonIcon, Description as DescriptionIcon,
    Inbox as InboxIcon, Download as DownloadIcon,
    Send as SendIcon, CheckCircle as CheckCircleIcon,
    AccessTime as AccessTimeIcon,
    ContactPage as ContactIcon
} from '@mui/icons-material';
import { jwtDecode } from 'jwt-decode';
import { calculateWorkingDays } from '../utils/dateUtils';
import {
    adminGetUsers,
    adminGetPlans,
    getExternalDocs,
    uploadExternalDoc,
    sendExternalResponse,
    downloadExternalSource,
} from '../services/api';

interface User {
  id: number;
  iin: string;
  full_name: string;
  org_name: string;
  email: string;
  is_active: boolean;
}

const UsersTab = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const data = await adminGetUsers();
        setUsers(data);
      } catch {
        setError("Не удалось загрузить пользователей.");
      } finally {
        setLoading(false);
      }
    };
    loadUsers();
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

interface Plan {
  id: number;
  plan_name: string;
  year: number;
  created_at: string;
}

const PlansTab = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const data = await adminGetPlans();
        setPlans(data);
      } catch {
        setError("Не удалось загрузить планы.");
      } finally {
        setLoading(false);
      }
    };
    loadPlans();
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

interface ExternalDoc {
  id: number;
  bank_name: string;
  doc_type: string;
  sender_last_name?: string;
  sender_first_name?: string;
  sender_email?: string;
  sender_phone?: string;
  received_at: string;
  completed_at?: string;
  status: string;
  file_path: string;
}

const ExternalDocsTab = () => {
    const [docs, setDocs] = useState<ExternalDoc[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [error, setError] = useState('');

    const [file, setFile] = useState<File | null>(null);
    const [docType, setDocType] = useState('PSD');
    const [bankName, setBankName] = useState('');
    const [receivedAt, setReceivedAt] = useState('');
    const [notes, setNotes] = useState('');

    // Новые поля отправителя
    const [senderFirstName, setSenderFirstName] = useState('');
    const [senderLastName, setSenderLastName] = useState('');
    const [senderPatronymic, setSenderPatronymic] = useState('');
    const [senderEmail, setSenderEmail] = useState('');
    const [senderPhone, setSenderPhone] = useState('');
    const [externalId, setExternalId] = useState('');

    const loadDocs = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await getExternalDocs();
            setDocs(data);
        } catch {
            setError("Не удалось загрузить документы.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocs();
    }, []);

    const handleUpload = async () => {
        if (!file || !bankName || !receivedAt) return;
        try {
            await uploadExternalDoc(
                file, docType, bankName, receivedAt, notes,
                senderFirstName, senderLastName, senderPatronymic, senderEmail, senderPhone, externalId
            );
            setUploadOpen(false);
            loadDocs();
            resetForm();
        } catch {
            alert("Ошибка загрузки");
        }
    };

    const resetForm = () => {
        setFile(null);
        setBankName('');
        setReceivedAt('');
        setNotes('');
        setSenderFirstName('');
        setSenderLastName('');
        setSenderPatronymic('');
        setSenderEmail('');
        setSenderPhone('');
        setExternalId('');
    };

    const handleSendResponse = async (docId: number) => {
        if (window.confirm("Подтвердить отправку ответа? Статус изменится на 'Отправлен'.")) {
            try {
                await sendExternalResponse(docId);
                loadDocs();
            } catch {
                alert("Ошибка отправки ответа");
            }
        }
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
                            <TableCell>Банк / Объект</TableCell>
                            <TableCell>Отправитель</TableCell>
                            <TableCell>Дата получения</TableCell>
                            <TableCell>Рабочих дней</TableCell>
                            <TableCell>Статус</TableCell>
                            <TableCell align="right">Действия</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {docs.map((doc) => {
                            const days = calculateWorkingDays(doc.received_at, doc.completed_at || new Date());
                            const isOverdue = days > 10 && doc.status !== 'SENT';

                            return (
                                <TableRow key={doc.id}>
                                    <TableCell>{doc.id}</TableCell>
                                    <TableCell>
                                        <Typography variant="body2" fontWeight="bold">{doc.bank_name}</Typography>
                                        <Typography variant="caption" color="text.secondary">{doc.doc_type}</Typography>
                                    </TableCell>
                                    <TableCell>
                                        {doc.sender_last_name ? (
                                            <Box>
                                                <Typography variant="body2">{doc.sender_last_name} {doc.sender_first_name}</Typography>
                                                <Typography variant="caption" color="text.secondary">{doc.sender_email || doc.sender_phone}</Typography>
                                            </Box>
                                        ) : "—"}
                                    </TableCell>
                                    <TableCell>{new Date(doc.received_at).toLocaleString()}</TableCell>
                                    <TableCell>
                                        <Chip
                                            icon={<AccessTimeIcon />}
                                            label={`${days} раб. дн.`}
                                            color={isOverdue ? 'error' : 'default'}
                                            variant={isOverdue ? 'filled' : 'outlined'}
                                            size="small"
                                            sx={{ fontWeight: 'bold' }}
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
                                    <TableCell align="right">
                                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                                            <Tooltip title="Скачать файл">
                                                <IconButton size="small" onClick={() => downloadExternalSource(doc.id, doc.file_path.split('/').pop() || 'document')}>
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

            <Dialog open={uploadOpen} onClose={() => setUploadOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle>Загрузка внешнего документа</DialogTitle>
                <DialogContent>
                    <Grid container spacing={3} sx={{ mt: 0.5 }}>
                        <Grid size={{ xs: 12, md: 6 }}>
                            <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                <DescriptionIcon color="primary" fontSize="small" /> Основная информация
                            </Typography>
                            <Stack spacing={2}>
                                <TextField select label="Тип документа" value={docType} onChange={(e) => setDocType(e.target.value)} fullWidth size="small">
                                    <MenuItem value="PSD">ПСД (KENML)</MenuItem>
                                    <MenuItem value="SMETA">Смета (Excel)</MenuItem>
                                </TextField>
                                <TextField label="Номер документа (ID во внешней системе)" value={externalId} onChange={(e) => setExternalId(e.target.value)} fullWidth size="small" />
                                <TextField label="Наименование объекта / Банка" value={bankName} onChange={(e) => setBankName(e.target.value)} fullWidth size="small" />
                                <TextField label="Дата и время получения" type="datetime-local" value={receivedAt} onChange={(e) => setReceivedAt(e.target.value)} fullWidth size="small" InputLabelProps={{ shrink: true }} />
                                <TextField label="Примечание" value={notes} onChange={(e) => setNotes(e.target.value)} fullWidth multiline rows={2} size="small" />
                            </Stack>
                        </Grid>

                        <Grid size={{ xs: 12, md: 6 }}>
                            <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                <ContactIcon color="primary" fontSize="small" /> Данные отправителя
                            </Typography>
                            <Stack spacing={2}>
                                <TextField label="Фамилия" value={senderLastName} onChange={(e) => setSenderLastName(e.target.value)} fullWidth size="small" />
                                <TextField label="Имя" value={senderFirstName} onChange={(e) => setSenderFirstName(e.target.value)} fullWidth size="small" />
                                <TextField label="Отчество" value={senderPatronymic} onChange={(e) => setSenderPatronymic(e.target.value)} fullWidth size="small" />
                                <TextField label="Email" type="email" value={senderEmail} onChange={(e) => setSenderEmail(e.target.value)} fullWidth size="small" />
                                <TextField label="Телефон" value={senderPhone} onChange={(e) => setSenderPhone(e.target.value)} fullWidth size="small" />
                            </Stack>
                        </Grid>

                        <Grid size={{ xs: 12 }}>
                            <Divider sx={{ my: 1 }} />
                            <Box sx={{ mt: 1 }}>
                                <Button variant="outlined" component="label" fullWidth sx={{ borderStyle: 'dashed', py: 2 }}>
                                    {file ? `Файл: ${file.name}` : "Выбрать файл документа"}
                                    <input type="file" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
                                </Button>
                            </Box>
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions sx={{ p: 2 }}>
                    <Button onClick={() => setUploadOpen(false)}>Отмена</Button>
                    <Button onClick={handleUpload} variant="contained" disabled={!file || !bankName || !receivedAt}>
                        Загрузить в систему
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default function AdminPage() {
  const [tab, setTab] = useState(0);

  let isAdmin = false;
  try {
    const token = localStorage.getItem('token');
    if (token) {
      const decoded: { is_admin?: boolean } = jwtDecode(token);
      isAdmin = decoded.is_admin === true;
    }
  } catch { /* ignore */ }

  // Индексы табов зависят от видимости "Пользователи"
  // isAdmin:    0=Входящие, 1=Пользователи, 2=Все планы
  // !isAdmin:   0=Входящие, 1=Все планы
  const plansTabIndex = isAdmin ? 2 : 1;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom fontWeight="bold" sx={{ mb: 4 }}>
        Проекты
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(_event, v) => setTab(v)} centered>
          <Tab icon={<InboxIcon />} label="Входящие документы" />
          {isAdmin && <Tab icon={<PersonIcon />} label="Пользователи" />}
          <Tab icon={<DescriptionIcon />} label="Все планы" />
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        {tab === 0 && <ExternalDocsTab />}
        {isAdmin && tab === 1 && <UsersTab />}
        {tab === plansTabIndex && <PlansTab />}
      </Box>
    </Container>
  );
}
