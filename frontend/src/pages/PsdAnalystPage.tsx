/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/ban-ts-comment */
/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
/* eslint-disable @typescript-eslint/no-unsafe-return */
/* eslint-disable @typescript-eslint/no-implied-eval */
import {useState, useEffect, useRef} from 'react';
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Button, Tabs, Tab, Chip, IconButton, Dialog,
    DialogTitle, DialogContent, TextField, DialogActions, Tooltip,
    Pagination, Divider, Card, CardContent, InputAdornment,
    LinearProgress, CircularProgress, Stack, FormControlLabel, Switch,
    ToggleButtonGroup, ToggleButton, Select, MenuItem, FormControl
} from '@mui/material';
import {
    Delete as DeleteIcon, Download as DownloadIcon,
    Search as SearchIcon, Refresh as RefreshIcon, Business as BusinessIcon,
    Close as CloseIcon, Edit as EditIcon,
    Visibility as VisibilityIcon,
    AutoAwesome as AutoIcon,
    QrCode as AgskIcon,
    Category as CategoryIcon,
    InfoOutlined as InfoIcon,
    FileDownload as FileDownloadIcon,
    Description as DescriptionIcon,
    Science as ScienceIcon,
    Person as PersonIcon,
    Email as EmailIcon,
    Phone as PhoneIcon,
    AssignmentInd as AssignIcon,
    Group as GroupIcon,
    PersonOutline as PersonOutlineIcon,
    AccessTime as AccessTimeIcon,
    CheckCircle as CheckCircleIcon,
    Send as SendIcon,
    Check as ApprovedIcon,
    SwapHoriz as DelegateIcon,
    Comment as CommentIcon,
    ExpandLess as ExpandLessIcon,
    ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import {useTranslation} from '../i18n';
import Header from '../components/Header';
import * as psdApi from './psd-analyst/api';
import AssignDialog from './psd-analyst/dialogs/AssignDialog';
import RejectDialog from './psd-analyst/dialogs/RejectDialog';
import DelegateDialog from './psd-analyst/dialogs/DelegateDialog';
import UploadDialog from './psd-analyst/dialogs/UploadDialog';
import {calculateWorkingDays} from '../utils/dateUtils';
import {UserRole} from '../services/api.types'; // Значение для runtime
import type {User, ExternalDocument, AgskEnstruMatchItem} from '../services/api.types'; // Только типы

// Локальные типы / хуки / утилиты страницы PSD-аналитика
import type {AgskMatch, ReestrResult, SearchMode} from './psd-analyst/types';
import {SEARCH_TABS} from './psd-analyst/types';
import {useDebounce} from './psd-analyst/hooks';
import {Highlight, ClassifierText} from './psd-analyst/components';
import {getItemStatus, getDvcColor, getStatusChip} from './psd-analyst/utils';

const PsdAnalystPage: React.FC = () => {
    const {t: _t} = useTranslation();
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [activeTab, setActiveTab] = useState(0);
    const [documents, setDocuments] = useState<ExternalDocument[]>([]);
    const [matches, setMatches] = useState<AgskMatch[]>([]);
    const [selectedDoc, setSelectedDoc] = useState<ExternalDocument | null>(null);
    const [listLoading, setListLoading] = useState(false);
    const [parsing, setParsing] = useState(false);
    const [exportLoading, setExportLoading] = useState(false);
    const [docxLoading, setDocxLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [showTests, setShowTests] = useState(false);
    const [assignedToMe, setAssignedToMe] = useState(false);
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

    // Состояния для диалогов директора
    const [assignDialogOpen, setAssignDialogOpen] = useState(false);
    const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
    const [delegateDialogOpen, setDelegateDialogOpen] = useState(false);
    const [targetDoc, setTargetDoc] = useState<ExternalDocument | null>(null);
    const [analysts, setAnalysts] = useState<{ id: number, full_name: string }[]>([]);
    // State диалогов (selectedAnalystId / deadlineDays / rejectComment / delegate*)
    // инкапсулирован внутри компонентов ./psd-analyst/dialogs/*.tsx

    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [editingMatch, setEditingMatch] = useState<AgskMatch | null>(null);
    const [reestrResults, setReestrResults] = useState<ReestrResult[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any

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
    const [uploading, setUploading] = useState(false);
    // testProjectName / selectedFile инкапсулированы в UploadDialog

    // Состояния для комментария аналитика
    const [analystComment, setAnalystComment] = useState('');
    const [savingComment, setSavingComment] = useState(false);

    // Новая система сопоставлений
    const [pendingMatchCount, setPendingMatchCount] = useState(0);
    const [matchesLibrary, setMatchesLibrary] = useState<AgskEnstruMatchItem[]>([]);
    const [matchesLibraryTotal, setMatchesLibraryTotal] = useState(0);
    const [matchesLibraryPage, setMatchesLibraryPage] = useState(1);
    const [matchesLoading, setMatchesLoading] = useState(false);
    const [matchDateFilter, setMatchDateFilter] = useState<'all' | 'today'>('all');
    const LIBRARY_PAGE_SIZE = 25;
    const [approvingId, setApprovingId] = useState<number | null>(null);
    const [librarySearch, setLibrarySearch] = useState('');
    const [libraryStatusFilter, setLibraryStatusFilter] = useState<string>('all');
    const [libraryAnalystFilter, setLibraryAnalystFilter] = useState<number | null>(null);
    const debouncedLibrarySearch = useDebounce(librarySearch, 400);

    // Диалог создания связки АГСК→ЕНСТРУ
    const [createMatchOpen, setCreateMatchOpen] = useState(false);
    const [newMatchAgsk, setNewMatchAgsk] = useState<{code: string; full_name: string} | null>(null);
    const [newMatchEnstruList, setNewMatchEnstruList] = useState<{code: string; name_rus: string}[]>([]);
    const [agskOptions, setAgskOptions] = useState<{id: number; code: string; name_ru: string; full_name: string}[]>([]);
    const [enstrupOptions, setEnstruOptions] = useState<{id: number; code: string; name_rus: string; detail_rus?: string}[]>([]);
    const [agskInputVal, setAgskInputVal] = useState('');
    const [enstrupInputVal, setEnstruInputVal] = useState('');
    const [agskSearchLoading, setAgskSearchLoading] = useState(false);
    const [enstrupSearchLoading, setEnstruSearchLoading] = useState(false);
    const [creatingMatch, setCreatingMatch] = useState(false);
    const [existingAgskMatches, setExistingAgskMatches] = useState<psdApi.ExistingAgskMatch[]>([]);
    const [existingAgskLoading, setExistingAgskLoading] = useState(false);
    const debouncedAgskInput = useDebounce(agskInputVal, 350);
    const debouncedEnstruInput = useDebounce(enstrupInputVal, 350);

    const requestCounter = useRef(0);

    useEffect(() => {
        loadCurrentUser();
        loadDocuments();
        loadAnalysts();
    }, [showTests, assignedToMe]);

    useEffect(() => {
        if (selectedDoc) {
            loadMatches(selectedDoc.id);
            // Загружаем комментарий аналитика из выбранного документа
            setAnalystComment(selectedDoc.analyst_comment || '');
        }
    }, [selectedDoc, onlyUnmatched, page, debouncedAgskSearch]);

    // Сброс поиска происходит только при РУЧНОЙ смене вкладки режима (см. onChange в Tabs ниже),
    // НЕ при программной установке searchMode из openEditDialog — иначе pre-fill не работает.

    useEffect(() => {
        const archiveTabIndex = selectedDoc ? 2 : 1;
        if (activeTab === archiveTabIndex) {
            loadMatchesLibrary();
        }
    }, [activeTab, matchDateFilter, selectedDoc, matchesLibraryPage, debouncedLibrarySearch, libraryStatusFilter, libraryAnalystFilter]);

    useEffect(() => {
        if (!debouncedAgskInput || debouncedAgskInput.length < 2) { setAgskOptions([]); return; }
        setAgskSearchLoading(true);
        psdApi.searchAgsk(debouncedAgskInput).then(setAgskOptions).finally(() => setAgskSearchLoading(false));
    }, [debouncedAgskInput]);

    useEffect(() => {
        if (!newMatchAgsk) { setExistingAgskMatches([]); return; }
        setExistingAgskLoading(true);
        psdApi.fetchMatchesByAgsk(newMatchAgsk.code)
            .then(data => {
                setExistingAgskMatches(data);
                // Авто-добавляем отклонённые в список выбранных? Нет — пусть пользователь сам решит.
            })
            .finally(() => setExistingAgskLoading(false));
    }, [newMatchAgsk]);

    useEffect(() => {
        if (!debouncedEnstruInput || debouncedEnstruInput.length < 2) { setEnstruOptions([]); return; }
        setEnstruSearchLoading(true);
        psdApi.searchEnstru(debouncedEnstruInput).then(setEnstruOptions).finally(() => setEnstruSearchLoading(false));
    }, [debouncedEnstruInput]);

    useEffect(() => {
        const minLen = searchMode === 'agsk' ? 3 : 2;
        if (debouncedReestrSearch.length >= minLen) handleSearchReestr();
        else if (debouncedReestrSearch.length === 0) setReestrResults([]);
    }, [debouncedReestrSearch, searchMode]);

    const loadCurrentUser = async () => {
        const user = await psdApi.fetchCurrentUser();
        setCurrentUser(user);
    };

    const loadAnalysts = async () => {
        setAnalysts(await psdApi.fetchAnalysts());
    };

    const loadDocuments = async () => {
        setListLoading(true);
        try {
            setDocuments(await psdApi.fetchDocuments(assignedToMe, showTests));
        } finally {
            setListLoading(false);
        }
    };

    const loadMatches = async (docId: number) => {
        const currentRequestId = ++requestCounter.current;
        setListLoading(true);
        try {
            const data = await psdApi.fetchDocumentItems(docId, {
                only_unmatched: onlyUnmatched,
                skip: (page - 1) * 50,
                limit: 50,
                search: debouncedAgskSearch || undefined,
            });
            if (currentRequestId === requestCounter.current) {
                setMatches(data.items);
                setTotalCount(data.total);
                setPendingMatchCount(data.pending_match_count ?? 0);
            }
        } finally {
            if (currentRequestId === requestCounter.current) {
                setListLoading(false);
            }
        }
    };

    // is_director приходит с бэкенда и учитывает делегирование полномочий
    const isDirector = currentUser?.is_director === true || currentUser?.role === UserRole.ADMIN;
    // Только настоящий директор (по роли), не делегированный
    const isRealDirector = currentUser?.role?.toLowerCase() === 'director_drvc' || currentUser?.role === UserRole.ADMIN;
    // Менеджер аналитиков — утверждает ручные сопоставления
    const isAnalystManager = currentUser?.role === UserRole.ANALYST_MANAGER || currentUser?.role === UserRole.ADMIN;

    // --- Действия Workflow ---

    const handleAssignAnalyst = async (analystId: number, days: number) => {
        if (!targetDoc) return;
        setActionLoading(true);
        try {
            await psdApi.assignAnalyst(targetDoc.id, analystId, days);
            setAssignDialogOpen(false);
            loadDocuments();
            alert('Аналитик успешно назначен');
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Unknown error';
            alert('Ошибка: ' + errorMsg);
        } finally {
            setActionLoading(false);
        }
    };

    const handleSubmitForApproval = async (docId: number) => {
        if (!window.confirm('Отправить документ на утверждение директору?')) return;
        setActionLoading(true);
        try {
            await psdApi.submitForApproval(docId);
            await loadDocuments(); // Ждем завершения загрузки
            if (selectedDoc?.id === docId) setSelectedDoc(null);
            setActiveTab(0);
            alert('Документ отправлен на утверждение');
        } catch (error: unknown) {
            const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
            if (axiosError.response?.status === 400) {
                const detail = axiosError.response?.data?.detail;
                if (detail && detail.includes('необработанные позиции')) {
                    alert('❌ ' + detail);
                } else {
                    alert('Ошибка: ' + (detail || 'Не удалось отправить на утверждение'));
                }
            } else {
                alert('Ошибка при отправке на утверждение');
            }
        } finally {
            setActionLoading(false);
        }
    };

    const handleApprove = async (docId: number) => {
        if (!window.confirm('Вы уверены, что хотите утвердить данный документ? Будет сформирован финальный ZIP-архив.')) return;
        setActionLoading(true);
        try {
            await psdApi.approveDocument(docId);
            await loadDocuments();
            alert('Документ успешно утвержден');
        } finally {
            setActionLoading(false);
        }
    };

    const handleReject = async (comment: string) => {
        if (!targetDoc) return;
        setActionLoading(true);
        try {
            await psdApi.rejectDocument(targetDoc.id, comment);
            setRejectDialogOpen(false);
            await loadDocuments();
            alert('Документ возвращен на доработку');
        } finally {
            setActionLoading(false);
        }
    };

    const handleSendToDo = async (docId: number) => {
        if (!window.confirm('Отправить результат анализа в дочернюю организацию?\n\nZIP архив с заключением будет отправлен на callback URL, указанный при загрузке документа.')) return;
        setActionLoading(true);
        try {
            const res = await psdApi.sendToDo(docId);
            await loadDocuments();
            alert(`✅ Результат успешно отправлен!\n\nCallback URL: ${res.data.callback_url}`);
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Unknown error';
            alert('❌ Ошибка отправки: ' + errorMsg);
        } finally {
            setActionLoading(false);
        }
    };

    const handleDelegate = async (toUserId: number, days: number) => {
        setActionLoading(true);
        try {
            await psdApi.delegateAuthority(toUserId, days);
            setDelegateDialogOpen(false);
            alert('Полномочия успешно делегированы');
        } finally {
            setActionLoading(false);
        }
    };

    // Скачивает blob с сервера и сохраняет под именем filename
    const downloadBlob = (data: Blob, filename: string) => {
        const url = window.URL.createObjectURL(new Blob([data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    };

    const handleDownloadResultZip = async (docId: number) => {
        try {
            const response = await psdApi.downloadResultZip(docId);
            downloadBlob(response.data, `Analysis_Result_${docId}.zip`);
        } catch {
            alert('Ошибка при скачивании файла');
        }
    };

    const handleDeleteDocument = async (docId: number) => {
        if (!window.confirm('Вы уверены, что хотите удалить этот проект? Это действие необратимо.')) return;
        try {
            await psdApi.deleteDocument(docId);
            if (selectedDoc?.id === docId) setSelectedDoc(null);
            loadDocuments();
        } catch {
            alert('Ошибка при удалении');
        }
    };

    const handleParse = async () => {
        if (!selectedDoc) return;
        setParsing(true);
        try {
            await psdApi.parseDocument(selectedDoc.id);
            await loadMatches(selectedDoc.id);
        } finally {
            setParsing(false);
        }
    };

    const handleUploadTest = async (file: File, projectName: string) => {
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('project_name', projectName);

            const res = await psdApi.uploadTest(formData);

            setUploadDialogOpen(false);
            setShowTests(true);
            await loadDocuments();

            if (res.data) {
                setSelectedDoc(res.data);
                setActiveTab(1);
            }
        } catch {
            alert('Ошибка при загрузке');
        } finally {
            setUploading(false);
        }
    };

    const openEditDialog = async (match: AgskMatch) => {
        const itemId = match.item_id || match.id;
        let freshItem = match;
        try {
            // Загружаем актуальные данные позиции (включая current_manual_match)
            const fresh = await psdApi.fetchDocumentItem(match.document_id!, itemId!);
            freshItem = {...match, ...fresh};
            setEditingMatch(freshItem);
        } catch {
            setEditingMatch(match);
        }
        setEditDialogOpen(true);
        setReestrResults([]);

        // Определяем начальный поиск по типу позиции.
        let initialMode: SearchMode = 'all';
        let initialQuery = '';
        if ((freshItem.match_type === 'auto' || freshItem.match_type === 'auto_ktp')
            && freshItem.code_sn && !(freshItem.current_manual_matches?.length)) {
            // Авто-совпадение по АГСК: ищем по АГСК-коду чтобы сразу показать список КТП поставщиков
            initialMode = 'agsk';
            initialQuery = freshItem.code_sn;
        } else if (freshItem.match_type === 'suggested' && freshItem.enstru_code && !(freshItem.current_manual_matches?.length)) {
            // Подсказка из библиотеки — ищем по ЕНСТРУ-коду
            initialMode = 'all';
            initialQuery = freshItem.enstru_code;
        }
        setSearchMode(initialMode);
        setReestrSearch(initialQuery);

        // Запускаем поиск сразу, не дожидаясь debounce/useEffect.
        // ВАЖНО: если у предыдущего открытия диалога было то же значение поиска —
        // React не пересоздаёт state, useDebounce не срабатывает, useEffect не запускается,
        // и старый/пустой список результатов остаётся. Поэтому вызываем явно.
        const minLen = initialMode === 'agsk' ? 3 : 2;
        if (initialQuery.length >= minLen) {
            handleSearchReestr(initialQuery, initialMode);
        }
    };

    const handleSearchReestr = async (overrideQuery?: string, overrideMode?: SearchMode) => {
        const q = overrideQuery ?? debouncedReestrSearch;
        const m = overrideMode ?? searchMode;
        setReestrLoading(true);
        try {
            setReestrResults(await psdApi.searchEnstruInReestr(q, m));
        } finally {
            setReestrLoading(false);
        }
    };

    // Функция для сохранения отметки "Нет в реестре КТП"
    const saveNotInKtpRegistry = async (itemId: number, value: boolean) => {
        // Оптимистично обновляем UI сразу
        const currentId = editingMatch?.item_id || editingMatch?.id;
        if (editingMatch && currentId === itemId) {
            setEditingMatch({...editingMatch, not_in_ktp_registry: value});
        }

        try {
            await psdApi.setNotInKtpRegistry(itemId, value);
            if (selectedDoc) {
                loadMatches(selectedDoc.id);
            }
        } catch {
            // При ошибке возвращаем старое значение
            // console.error('Failed to save not_in_ktp_registry');
            if (editingMatch && currentId === itemId) {
                setEditingMatch({...editingMatch, not_in_ktp_registry: !value});
            }
            alert('Ошибка при сохранении отметки');
        }
    };

    // ── Ручные сопоставления с approval-воркфлоу ────────────────────────────

    const loadMatchesLibrary = async () => {
        setMatchesLoading(true);
        try {
            const data = await psdApi.fetchMatchesLibrary({
                date_filter: matchDateFilter,
                skip: (matchesLibraryPage - 1) * LIBRARY_PAGE_SIZE,
                limit: LIBRARY_PAGE_SIZE,
                search: debouncedLibrarySearch || undefined,
                status_filter: libraryStatusFilter !== 'all' ? libraryStatusFilter : undefined,
                analyst_id: libraryAnalystFilter ?? undefined,
            });
            setMatchesLibrary(data.items);
            setMatchesLibraryTotal(data.total);
            // Авто-раскрыть все группы если их немного
            const uniqueAgsk = [...new Set(data.items.map((i: AgskEnstruMatchItem) => i.agsk_code))];
            if (uniqueAgsk.length <= 15) setExpandedGroups(new Set(uniqueAgsk));
        } finally {
            setMatchesLoading(false);
        }
    };

    const handleCreateMatch = async () => {
        if (!newMatchAgsk || newMatchEnstruList.length === 0) return;
        setCreatingMatch(true);
        try {
            const result = await psdApi.createAgskEnstruMatchBatch(
                newMatchAgsk.code,
                newMatchEnstruList.map(e => e.code),
            );
            setCreateMatchOpen(false);
            setNewMatchAgsk(null);
            setNewMatchEnstruList([]);
            setAgskInputVal('');
            setEnstruInputVal('');
            setExistingAgskMatches([]);
            loadMatchesLibrary();
            if (result.skipped?.length > 0) {
                alert(`Создано: ${result.created.length}. Уже существовали: ${result.skipped.join(', ')}`);
            }
        } catch (err: unknown) {
            const msg = (err as {response?: {data?: {detail?: string}}})?.response?.data?.detail || 'Ошибка создания';
            alert(msg);
        } finally {
            setCreatingMatch(false);
        }
    };

    const approveMatch = async (matchId: number) => {
        setApprovingId(matchId);
        try {
            await psdApi.approveLibraryMatch(matchId);
            setMatchesLibrary(prev => prev.map(m =>
                m.id === matchId ? {...m, is_approved: true, status: 'approved'} : m
            ));
            if (selectedDoc) loadMatches(selectedDoc.id);
        } catch {
            alert('Ошибка при утверждении');
        } finally {
            setApprovingId(null);
        }
    };

    const rejectMatch = async (matchId: number) => {
        setApprovingId(matchId);
        try {
            await psdApi.rejectLibraryMatch(matchId);
            setMatchesLibrary(prev => prev.map(m =>
                m.id === matchId ? {...m, is_active: false, status: 'rejected'} : m
            ));
            if (selectedDoc) loadMatches(selectedDoc.id);
        } catch {
            alert('Ошибка при отклонении');
        } finally {
            setApprovingId(null);
        }
    };

    const saveMatch = async (item: ReestrResult) => {
        if (!editingMatch) return;
        const itemId = editingMatch.item_id || editingMatch.id;
        if (!itemId) return;
        try {
            await psdApi.saveSupplierMatch(itemId, {
                enstru_code: item.enstru_code,
                ktp_id: item.ktp_id || null,
                supplier_bin: item.bin || null,
                supplier_name: item.company || null,
                supplier_product: item.product || null,
                dvc_percent: item.dvc_percent || null,
            });
            // Обновляем editingMatch актуальными данными (включая current_manual_matches)
            const fresh = await psdApi.fetchDocumentItem(editingMatch.document_id!, itemId);
            setEditingMatch({...editingMatch, ...fresh});
            // Обновляем таблицу
            if (selectedDoc) loadMatches(selectedDoc.id);
            // Убираем выбранного поставщика из результатов поиска
            setReestrResults(prev => prev.filter((r: any) => !(r.enstru_code === item.enstru_code && r.ktp_id === item.ktp_id)));
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            if (err?.response?.status === 409) {
                alert(`${detail || 'Этот поставщик уже выбран для данной позиции'}`);
            } else {
                alert('Ошибка при выборе поставщика');
            }
        }
    };

    const deleteMatch = async (matchId: number) => {
        if (!window.confirm('Удалить это сопоставление?')) return;
        try {
            await psdApi.deleteLibraryMatch(matchId);
            // Мгновенно убираем из списка локально
            setEditingMatch(prev => prev ? {
                ...prev,
                current_manual_matches: (prev.current_manual_matches || []).filter(m => m.id !== matchId)
            } : prev);
            // Обновляем главную таблицу
            if (selectedDoc) loadMatches(selectedDoc.id);
            // Восстанавливаем удалённый результат в поиске
            if (debouncedReestrSearch.length >= 2) {
                handleSearchReestr();
            }
        } catch {
            alert('Ошибка при удалении сопоставления');
        }
    };

    const handleExportFullReport = async (docId?: number) => {
        setExportLoading(true);
        try {
            const response = await psdApi.exportFullReport(docId);
            // Извлекаем имя файла из Content-Disposition
            const cd = response.headers['content-disposition'];
            let filename = docId ? `psd_report_doc_${docId}.xlsx` : 'psd_full_report.xlsx';
            if (cd) {
                const m = cd.match(/filename="(.+)"/);
                if (m && m[1]) filename = m[1];
            }
            downloadBlob(response.data, filename);
        } catch {
            alert('Ошибка при выгрузке отчета');
        } finally {
            setExportLoading(false);
        }
    };

    const handleDownloadConclusion = async (docId: number) => {
        setDocxLoading(true);
        try {
            const response = await psdApi.downloadConclusion(docId);
            downloadBlob(response.data, `Заключение_ПСД_${docId}.docx`);
        } catch {
            alert('Ошибка при генерации заключения');
        } finally {
            setDocxLoading(false);
        }
    };

    const handleSaveAnalystComment = async () => {
        if (!selectedDoc) return;
        setSavingComment(true);
        try {
            await psdApi.saveAnalystComment(selectedDoc.id, analystComment);
            setSelectedDoc({...selectedDoc, analyst_comment: analystComment});
            alert('Комментарий сохранен');
        } catch {
            alert('Ошибка при сохранении комментария');
        } finally {
            setSavingComment(false);
        }
    };

    // getItemStatus / getStatusChip / getDvcColor / ClassifierText / Highlight
    // вынесены в ./psd-analyst/utils.tsx и ./psd-analyst/components.tsx

    const currentSearchTab = SEARCH_TABS.find(t => t.mode === searchMode)!;

    // Диалог в режиме «только просмотр»: для auto/auto_ktp АГСК прямо сопоставлен
    // с реестром КТП — аналитик не выбирает поставщика, а только смотрит результат.
    const isReadOnlyDialog =
        editingMatch?.match_type === 'auto' || editingMatch?.match_type === 'auto_ktp';

    return (
        <Box sx={{bgcolor: '#f5f7f9', minHeight: '100vh'}}>
            <Header/>
            <Box sx={{p: 2}}>
                <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2}}>
                    <Box sx={{display: 'flex', alignItems: 'center', gap: 2}}>
                        <Typography variant="h5" fontWeight="bold" color="#1a237e">
                            Аналитика ПСД
                        </Typography>

                        <Divider orientation="vertical" flexItem sx={{mx: 1, height: 24, alignSelf: 'center'}}/>

                        <ToggleButtonGroup
                            size="small"
                            value={assignedToMe}
                            exclusive
                            onChange={(_, v) => v !== null && setAssignedToMe(v)}
                            sx={{bgcolor: 'white'}}
                        >
                            <ToggleButton value={false} sx={{px: 2, textTransform: 'none', gap: 1}}>
                                <GroupIcon fontSize="small"/> Все проекты
                            </ToggleButton>
                            <ToggleButton value={true} sx={{px: 2, textTransform: 'none', gap: 1}}>
                                <PersonOutlineIcon fontSize="small"/> Мои
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
                                <Typography sx={{
                                    fontSize: '0.8rem',
                                    fontWeight: 'bold',
                                    color: showTests ? 'warning.main' : 'text.secondary'
                                }}>
                                    Тестовые
                                </Typography>
                            }
                            sx={{
                                ml: 1,
                                bgcolor: showTests ? '#fff3e0' : 'transparent',
                                px: 1.5,
                                borderRadius: 5,
                                py: 0.2,
                                border: '1px solid',
                                borderColor: showTests ? 'warning.light' : 'transparent'
                            }}
                        />
                    </Box>

                    <Stack direction="row" spacing={1}>
                        {isRealDirector && (
                            <Button
                                size="small"
                                variant="outlined"
                                color="primary"
                                startIcon={<DelegateIcon/>}
                                onClick={() => setDelegateDialogOpen(true)}
                                sx={{bgcolor: 'white', textTransform: 'none'}}>
                                Делегировать
                            </Button>
                        )}
                        <Button
                            size="small"
                            variant="outlined"
                            color="warning"
                            startIcon={<ScienceIcon/>}
                            onClick={() => setUploadDialogOpen(true)}
                            sx={{bgcolor: 'white', textTransform: 'none'}}>
                            Создать тест
                        </Button>
                        <Button size="small" variant="outlined" startIcon={<RefreshIcon/>} onClick={loadDocuments}
                                sx={{bgcolor: 'white', textTransform: 'none'}}>
                            Обновить
                        </Button>
                    </Stack>
                </Box>

                <Tabs value={activeTab}
                      onChange={(_, v) => setActiveTab(v)}
                      sx={{mb: 2, bgcolor: 'white', borderRadius: 2, minHeight: 40}}>
                    <Tab label="Документы" sx={{textTransform: 'none', minHeight: 40}}/>
                    {selectedDoc && (
                        <Tab
                            label={selectedDoc.document_number || `Документ №${selectedDoc.id}`}
                            sx={{
                                textTransform: 'none',
                                minHeight: 40,
                                bgcolor: '#e3f2fd',
                                borderRadius: '4px 4px 0 0',
                                fontWeight: 'bold',
                                color: '#1565c0 !important'
                            }}
                        />
                    )}
                    <Tab label="Библиотека" sx={{textTransform: 'none', minHeight: 40}}/>
                </Tabs>

                {activeTab === 0 && (
                    <TableContainer component={Paper} elevation={0}
                                    sx={{border: '1px solid #e0e0e0', borderRadius: 2, position: 'relative'}}>
                        {listLoading &&
                            <LinearProgress sx={{position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1}}/>}
                        <Table size="small">
                            <TableHead sx={{bgcolor: '#fafafa'}}>
                                <TableRow>
                                    <TableCell sx={{fontWeight: 'bold'}}>ID</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Тип / № документа ДО</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Проект / Отправитель</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Контакты Отправителя</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Аналитик</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Срок / Дедлайн</TableCell>
                                    <TableCell sx={{fontWeight: 'bold'}}>Статус</TableCell>
                                    <TableCell align="right" sx={{fontWeight: 'bold'}}>Действие</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {(() => {
                                    // Группируем документы по проекту (external_id + bank_name)
                                    const groups = new Map<string, {
                                        projectKey: string,
                                        bankName: string,
                                        externalId: string | null,
                                        docs: typeof documents
                                    }>()
                                    documents.forEach(doc => {
                                        const key = doc.external_id ? `${doc.bank_name}::${doc.external_id}` : `single::${doc.id}`;
                                        if (!groups.has(key)) {
                                            groups.set(key, {
                                                projectKey: key,
                                                bankName: doc.bank_name,
                                                externalId: doc.external_id ?? null,
                                                docs: []
                                            });
                                        }
                                        groups.get(key)!.docs.push(doc);
                                    });

                                    const groupList = Array.from(groups.values()).sort((a, b) => {
                                        // Группы с external_id идут первыми, потом по дате первого документа
                                        if (a.externalId && !b.externalId) return -1;
                                        if (!a.externalId && b.externalId) return 1;
                                        return new Date(b.docs[0].received_at).getTime() - new Date(a.docs[0].received_at).getTime();
                                    });

                                    return groupList.flatMap(group => {
                                        const isExpanded = expandedGroups.has(group.projectKey);
                                        const isMultiDoc = group.docs.length > 1;

                                        const rows: React.ReactElement[] = [];

                                        // Заголовок группы (только если несколько документов с external_id)
                                        if (isMultiDoc) {
                                            const allAssigned = group.docs.every(d => d.assigned_to);
                                            const anyParsed = group.docs.some(d => d.status === 'PARSED' || d.status === 'ASSIGNED_TO_ANALYST');

                                            rows.push(
                                                <TableRow
                                                    key={`group-${group.projectKey}`}
                                                    sx={{
                                                        bgcolor: allAssigned ? '#e3f2fd' : anyParsed ? '#f5f5f5' : '#fff3e0',
                                                        cursor: 'pointer',
                                                        '&:hover': {bgcolor: '#e0e0e0'}
                                                    }}
                                                    onClick={() => {
                                                        const newSet = new Set(expandedGroups);
                                                        if (newSet.has(group.projectKey)) {
                                                            newSet.delete(group.projectKey);
                                                        } else {
                                                            newSet.add(group.projectKey);
                                                        }
                                                        setExpandedGroups(newSet);
                                                    }}
                                                >
                                                    <TableCell colSpan={8}>
                                                        <Box sx={{display: 'flex', alignItems: 'center', gap: 2}}>
                                                            <IconButton size="small">
                                                                {isExpanded ? <ExpandLessIcon/> : <ExpandMoreIcon/>}
                                                            </IconButton>
                                                            <Typography variant="subtitle2" fontWeight="bold">
                                                                Проект: {group.bankName}
                                                            </Typography>
                                                            <Chip
                                                                size="small"
                                                                label={`№ ${group.externalId}`}
                                                                color="primary"
                                                                variant="outlined"
                                                                sx={{fontFamily: 'monospace'}}
                                                            />
                                                            <Chip
                                                                size="small"
                                                                label={`${group.docs.length} файла`}
                                                                color="default"
                                                                variant="outlined"
                                                            />
                                                            {allAssigned && (
                                                                <Chip size="small" label="Назначен" color="success"
                                                                      variant="outlined"/>
                                                            )}
                                                            <Box sx={{ml: 'auto', display: 'flex', gap: 0.5}}>
                                                                {group.docs.map(d => (
                                                                    <Chip
                                                                        key={d.id}
                                                                        size="small"
                                                                        label={d.doc_type}
                                                                        color={d.doc_type === 'PSD' ? 'primary' : 'secondary'}
                                                                        sx={{fontSize: '0.7rem', height: 20}}
                                                                    />
                                                                ))}
                                                            </Box>
                                                        </Box>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        }

                                        // Строки документов (показываем всегда для одиночных, или если группа раскрыта)
                                        if (!isMultiDoc || isExpanded || !isMultiDoc) {
                                            group.docs.forEach(doc => {
                                                const days = calculateWorkingDays(doc.received_at, doc.completed_at || new Date().toISOString());

                                                let color: 'error' | 'warning' | 'default' = 'default';
                                                if (doc.status !== 'COMPLETED' && doc.deadline_days) {
                                                    if (days >= doc.deadline_days) color = 'error';
                                                    else if (days >= doc.deadline_days * 0.7) color = 'warning';
                                                }

                                                rows.push(
                                                    <TableRow
                                                        key={doc.id}
                                                        hover
                                                        sx={{
                                                            bgcolor: doc.is_test ? '#fffef0' : 'inherit',
                                                            ...(isMultiDoc && {pl: 4})
                                                        }}
                                                    >
                                                        <TableCell>
                                                            <Box sx={{display: 'flex', alignItems: 'center', gap: 1}}>
                                                                {isMultiDoc &&
                                                                    <Box sx={{width: 24}}/>} {/* Отступ для группы */}
                                                                #{doc.id}
                                                            </Box>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Box sx={{
                                                                display: 'flex',
                                                                flexDirection: 'column',
                                                                gap: 0.5
                                                            }}>
                                                                <Chip
                                                                    size="small"
                                                                    label={doc.doc_type}
                                                                    color={doc.doc_type === 'PSD' ? 'primary' : 'secondary'}
                                                                    sx={{fontWeight: 'bold', width: 'fit-content'}}
                                                                />
                                                                {doc.external_id && (
                                                                    <Typography variant="caption" color="text.secondary"
                                                                                sx={{fontFamily: 'monospace'}}>
                                                                        №: {doc.external_id}
                                                                    </Typography>
                                                                )}
                                                                <Typography variant="caption" color="text.disabled">
                                                                    {new Date(doc.received_at).toLocaleString('ru-RU')}
                                                                </Typography>
                                                            </Box>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Box sx={{
                                                                display: 'flex',
                                                                flexDirection: 'column',
                                                                gap: 0.5
                                                            }}>
                                                                <Box sx={{
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: 1
                                                                }}>
                                                                    {doc.is_test && <ScienceIcon
                                                                        sx={{fontSize: 16, color: 'warning.main'}}/>}
                                                                    <Typography variant="body2"
                                                                                fontWeight="bold">{doc.bank_name}</Typography>
                                                                </Box>
                                                                {(doc.sender_last_name || doc.sender_first_name) && (
                                                                    <Tooltip
                                                                        title={`${doc.sender_last_name || ''} ${doc.sender_first_name || ''} ${doc.sender_patronymic || ''}`}>
                                                                        <Box sx={{
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: 0.5
                                                                        }}>
                                                                            <PersonIcon sx={{
                                                                                fontSize: 14,
                                                                                color: 'text.secondary'
                                                                            }}/>
                                                                            <Typography variant="caption"
                                                                                        color="text.secondary">
                                                                                {doc.sender_last_name} {doc.sender_first_name?.charAt(0)}.
                                                                            </Typography>
                                                                        </Box>
                                                                    </Tooltip>
                                                                )}
                                                                {doc.notes && (
                                                                    <Tooltip title={doc.notes}>
                                                                        <Typography variant="caption"
                                                                                    color="text.secondary" sx={{
                                                                            fontStyle: 'italic',
                                                                            maxWidth: 200,
                                                                            overflow: 'hidden',
                                                                            textOverflow: 'ellipsis',
                                                                            whiteSpace: 'nowrap'
                                                                        }}>
                                                                            📝 {doc.notes}
                                                                        </Typography>
                                                                    </Tooltip>
                                                                )}
                                                            </Box>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Box sx={{
                                                                display: 'flex',
                                                                flexDirection: 'column',
                                                                gap: 0.5
                                                            }}>
                                                                {doc.sender_email && (
                                                                    <Box sx={{
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: 0.5
                                                                    }}>
                                                                        <EmailIcon sx={{
                                                                            fontSize: 14,
                                                                            color: 'text.secondary'
                                                                        }}/>
                                                                        <Typography variant="caption"
                                                                                    color="text.secondary">{doc.sender_email}</Typography>
                                                                    </Box>
                                                                )}
                                                                {doc.sender_phone && (
                                                                    <Box sx={{
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: 0.5
                                                                    }}>
                                                                        <PhoneIcon sx={{
                                                                            fontSize: 14,
                                                                            color: 'text.secondary'
                                                                        }}/>
                                                                        <Typography variant="caption"
                                                                                    color="text.secondary">{doc.sender_phone}</Typography>
                                                                    </Box>
                                                                )}
                                                                {doc.callback_url && (
                                                                    <Tooltip
                                                                        title={`Callback URL: ${doc.callback_url}`}>
                                                                        <Chip size="small" label="API ✓" color="success"
                                                                              sx={{
                                                                                  fontSize: '0.6rem',
                                                                                  height: 16,
                                                                                  width: 'fit-content'
                                                                              }}/>
                                                                    </Tooltip>
                                                                )}
                                                            </Box>
                                                        </TableCell>
                                                        <TableCell>
                                                            {doc.assigned_user_name ? (
                                                                <Chip
                                                                    size="small"
                                                                    icon={<PersonIcon
                                                                        sx={{fontSize: '14px !important'}}/>}
                                                                    label={doc.assigned_user_name}
                                                                    variant="outlined"
                                                                    color="primary"
                                                                    sx={{borderRadius: 1}}
                                                                />
                                                            ) : (
                                                                <Typography variant="caption" color="text.disabled">Не
                                                                    назначен</Typography>
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            <Stack spacing={0.5}>
                                                                <Chip
                                                                    icon={<AccessTimeIcon/>}
                                                                    label={`${days} раб. дн.`}
                                                                    color={color}
                                                                    variant={color !== 'default' ? 'filled' : 'outlined'}
                                                                    size="small"
                                                                    sx={{fontWeight: 'bold'}}
                                                                />
                                                                {doc.deadline_at && (
                                                                    <Typography variant="caption" sx={{
                                                                        color: color === 'error' ? 'error.main' : 'text.secondary',
                                                                        fontSize: '0.65rem'
                                                                    }}>
                                                                        До: {new Date(doc.deadline_at).toLocaleDateString()}
                                                                    </Typography>
                                                                )}
                                                            </Stack>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Stack spacing={0.5} alignItems="flex-start">
                                                                {getStatusChip(doc.status)}
                                                                {doc.analyst_comment && (
                                                                    <Tooltip title={doc.analyst_comment}>
                                                                        <Box sx={{
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: 0.5,
                                                                            cursor: 'help'
                                                                        }}>
                                                                            <CommentIcon sx={{
                                                                                fontSize: 12,
                                                                                color: 'primary.main'
                                                                            }}/>
                                                                            <Typography variant="caption"
                                                                                        color="primary"
                                                                                        sx={{fontSize: '0.6rem'}}>Коммент.
                                                                                аналитика</Typography>
                                                                        </Box>
                                                                    </Tooltip>
                                                                )}
                                                                {doc.director_comment && (
                                                                    <Tooltip title={doc.director_comment}>
                                                                        <Box sx={{
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: 0.5,
                                                                            cursor: 'help'
                                                                        }}>
                                                                            <CommentIcon sx={{
                                                                                fontSize: 12,
                                                                                color: 'error.main'
                                                                            }}/>
                                                                            <Typography variant="caption" color="error"
                                                                                        sx={{fontSize: '0.6rem'}}>Замечание</Typography>
                                                                        </Box>
                                                                    </Tooltip>
                                                                )}
                                                            </Stack>
                                                        </TableCell>
                                                        <TableCell align="right">
                                                            <Stack direction="row" spacing={1}
                                                                   justifyContent="flex-end">
                                                                {isDirector && (doc.status === 'NEW' || doc.status === 'PARSED') && (
                                                                    <Button size="small" variant="contained"
                                                                            color="primary" startIcon={<AssignIcon/>}
                                                                            onClick={() => {
                                                                                setTargetDoc(doc);
                                                                                setAssignDialogOpen(true);
                                                                            }}>
                                                                        Назначить
                                                                    </Button>
                                                                )}

                                                                {isDirector && doc.status === 'FOR_APPROVAL' && (
                                                                    <>
                                                                        <Button size="small" variant="contained"
                                                                                color="success"
                                                                                onClick={() => handleApprove(doc.id)}>
                                                                            Утвердить
                                                                        </Button>
                                                                        <Button size="small" variant="outlined"
                                                                                color="error" onClick={() => {
                                                                            setTargetDoc(doc);
                                                                            setRejectDialogOpen(true);
                                                                        }}>
                                                                            Вернуть
                                                                        </Button>
                                                                    </>
                                                                )}

                                                                {doc.status === 'COMPLETED' && (
                                                                    <Button size="small" variant="outlined"
                                                                            color="success" startIcon={<DownloadIcon/>}
                                                                            onClick={() => handleDownloadResultZip(doc.id)}>
                                                                        Результат
                                                                    </Button>
                                                                )}

                                                                {isRealDirector && (doc.status === 'APPROVED' || doc.status === 'COMPLETED') && (
                                                                    <Tooltip
                                                                        title={doc.callback_url ? 'Отправить ZIP архив в дочернюю организацию' : 'Callback URL не указан при загрузке документа'}>
                                  <span>
                                      <Button
                                          size="small"
                                          variant="contained"
                                          color="info"
                                          startIcon={<SendIcon/>}
                                          onClick={() => handleSendToDo(doc.id)}
                                          disabled={actionLoading || !doc.callback_url}
                                      >
                                          Отправить в ДО
                                      </Button>
                                  </span>
                                                                    </Tooltip>
                                                                )}

                                                                {doc.status === 'SENT' && (
                                                                    <Chip label="Отправлен в ДО" size="small"
                                                                          color="info" variant="outlined"/>
                                                                )}

                                                                {!isDirector && doc.assigned_to === currentUser?.id && (doc.status === 'ASSIGNED_TO_ANALYST' || doc.status === 'REJECTED_BY_DIRECTOR') && (
                                                                    <Button size="small" variant="contained"
                                                                            onClick={() => {
                                                                                setSelectedDoc(doc);
                                                                                setActiveTab(1);
                                                                            }}>
                                                                        Начать работу
                                                                    </Button>
                                                                )}

                                                                <Button size="small" variant="outlined"
                                                                        onClick={() => {
                                                                            setSelectedDoc(doc);
                                                                            setActiveTab(1);
                                                                        }}>
                                                                    Открыть
                                                                </Button>

                                                                <IconButton size="small" color="error"
                                                                            onClick={() => handleDeleteDocument(doc.id)}>
                                                                    <DeleteIcon fontSize="small"/>
                                                                </IconButton>
                                                            </Stack>
                                                        </TableCell>
                                                    </TableRow>
                                                );
                                            });
                                        }

                                        return rows;
                                    });
                                })()}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}

                {activeTab === 1 && selectedDoc && (
                    <Box>
                        <Paper sx={{
                            p: 1.5, mb: 2, display: 'flex', gap: 2, alignItems: 'center',
                            borderRadius: 2, flexWrap: 'wrap',
                            borderLeft: selectedDoc.is_test ? '6px solid #ffa000' : (selectedDoc.status === 'REJECTED_BY_DIRECTOR' ? '6px solid #f44336' : 'none')
                        }}>
                            <Box sx={{flexGrow: 1}}>
                                <Typography variant="subtitle2" fontWeight="bold"
                                            sx={{display: 'flex', alignItems: 'center', gap: 1}}>
                                    {selectedDoc.is_test && <ScienceIcon sx={{fontSize: 18, color: 'warning.main'}}/>}
                                    #{selectedDoc.id} {selectedDoc.bank_name}
                                </Typography>
                                <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                                    {getStatusChip(selectedDoc.status)}
                                    {selectedDoc.analyst_comment && (
                                        <Box sx={{
                                            bgcolor: '#e3f2fd',
                                            p: 0.5,
                                            borderRadius: 1,
                                            border: '1px solid #90caf9',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1
                                        }}>
                                            <CommentIcon sx={{fontSize: 14, color: 'primary.main'}}/>
                                            <Typography variant="caption" color="primary.main">
                                                <b>Комментарий
                                                    аналитика:</b> {selectedDoc.analyst_comment.length > 50 ? selectedDoc.analyst_comment.substring(0, 50) + '...' : selectedDoc.analyst_comment}
                                            </Typography>
                                        </Box>
                                    )}
                                    {selectedDoc.director_comment && (
                                        <Box sx={{
                                            bgcolor: '#fff5f5',
                                            p: 0.5,
                                            borderRadius: 1,
                                            border: '1px solid #ffcdd2',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1
                                        }}>
                                            <CommentIcon sx={{fontSize: 14, color: 'error.main'}}/>
                                            <Typography variant="caption" color="error.main">
                                                <b>Замечание:</b> {selectedDoc.director_comment}
                                            </Typography>
                                        </Box>
                                    )}
                                </Stack>
                            </Box>

                            <Divider orientation="vertical" flexItem/>

                            {totalCount === 0 ? (
                                <Button size="small" variant="contained" color="warning" onClick={handleParse}
                                        disabled={parsing}>
                                    {parsing ? 'Загрузка...' : 'Распарсить'}
                                </Button>
                            ) : (
                                <>
                                    <TextField
                                        size="small" placeholder="Поиск по позициям..." value={agskSearch}
                                        onChange={e => {
                                            setAgskSearch(e.target.value);
                                            setPage(1);
                                        }} sx={{width: 250}}
                                        InputProps={{
                                            startAdornment: <InputAdornment position="start"><SearchIcon
                                                fontSize="small"/></InputAdornment>
                                        }}
                                    />
                                    <Button size="small" variant={onlyUnmatched ? 'contained' : 'outlined'}
                                            color="error"
                                            startIcon={onlyUnmatched ? <CloseIcon fontSize="small"/> : undefined}
                                            onClick={() => {
                                                setOnlyUnmatched(!onlyUnmatched);
                                                setPage(1);
                                            }}
                                            sx={{textTransform: 'none'}}>
                                        {onlyUnmatched ? 'Сбросить фильтр' : 'Несопоставленные'}
                                    </Button>

                                    {/* Индикатор прогресса обработки */}
                                    {matches.length > 0 && (() => {
                                        // "Обработана" = есть активный выбор поставщика ИЛИ авто (АГСК в КТП)
                                        // ИЛИ не в реестре КТП ИЛИ не ТОВАР
                                        const isDone = (m: AgskMatch) =>
                                            (m.current_manual_matches?.some(mm => mm.status === 'active' || (mm.status as string) === 'approved')) ||
                                            m.match_type === 'auto' ||
                                            m.match_type === 'auto_ktp' ||
                                            m.match_type === 'manual' ||
                                            m.not_in_ktp_registry ||
                                            m.item_type === 'WORKS' ||
                                            m.item_type === 'SERVICES' ||
                                            m.item_type === 'OTHER' ||
                                            m.item_type === 'BALANCE';
                                        const doneCount = matches.filter(isDone).length;
                                        return (
                                            <Box sx={{display: 'flex', gap: 0.5, alignItems: 'center'}}>
                                                <Chip
                                                    size="small"
                                                    color={doneCount === matches.length ? 'success' : 'warning'}
                                                    label={`${doneCount}/${matches.length} обработано`}
                                                    sx={{fontSize: '0.7rem'}}
                                                />
                                            </Box>
                                        );
                                    })()}

                                    <Box sx={{flexGrow: 1}}/>

                                    <Stack direction="row" spacing={1}>
                                        <Button
                                            size="small"
                                            variant="outlined"
                                            color="secondary"
                                            startIcon={docxLoading ? <CircularProgress size={16} color="inherit"/> :
                                                <DescriptionIcon/>}
                                            disabled={docxLoading}
                                            onClick={() => handleDownloadConclusion(selectedDoc.id)}
                                            sx={{textTransform: 'none'}}
                                        >
                                            Заключение (DOCX)
                                        </Button>
                                        <Button
                                            size="small"
                                            variant="contained"
                                            color="success"
                                            startIcon={exportLoading ? <CircularProgress size={16} color="inherit"/> :
                                                <FileDownloadIcon/>}
                                            disabled={exportLoading}
                                            onClick={() => handleExportFullReport(selectedDoc.id)}
                                            sx={{textTransform: 'none'}}
                                        >
                                            Отчет (Excel)
                                        </Button>

                                        {!selectedDoc.is_test && (selectedDoc.status === 'ASSIGNED_TO_ANALYST' || selectedDoc.status === 'REJECTED_BY_DIRECTOR') && (
                                            <Box sx={{display: 'flex', alignItems: 'center', gap: 0.5}}>
                                                {pendingMatchCount > 0 && (
                                                    <Tooltip title={`${pendingMatchCount} пар АГСК→ЕНСТРУ ожидают утверждения в библиотеке (не блокирует отправку)`}>
                                                        <Chip
                                                            size="small"
                                                            label={`📚 ${pendingMatchCount}`}
                                                            color="info"
                                                            variant="outlined"
                                                            sx={{fontSize: '0.7rem', height: 22, cursor: 'help'}}
                                                        />
                                                    </Tooltip>
                                                )}
                                                <Button
                                                    size="small"
                                                    variant="contained"
                                                    color="primary"
                                                    startIcon={actionLoading ?
                                                        <CircularProgress size={16} color="inherit"/> : <SendIcon/>}
                                                    disabled={actionLoading}
                                                    onClick={() => handleSubmitForApproval(selectedDoc.id)}
                                                    sx={{textTransform: 'none'}}
                                                >
                                                    На утверждение
                                                </Button>
                                            </Box>
                                        )}

                                        {isDirector && selectedDoc.status === 'FOR_APPROVAL' && (
                                            <Button
                                                size="small"
                                                variant="contained"
                                                color="success"
                                                startIcon={actionLoading ?
                                                    <CircularProgress size={16} color="inherit"/> : <ApprovedIcon/>}
                                                disabled={actionLoading}
                                                onClick={() => handleApprove(selectedDoc.id)}
                                                sx={{textTransform: 'none'}}
                                            >
                                                Утвердить результат
                                            </Button>
                                        )}
                                    </Stack>
                                </>
                            )}
                        </Paper>

                        <TableContainer component={Paper} sx={{
                            borderRadius: 2,
                            border: '1px solid #e0e0e0',
                            position: 'relative',
                            minHeight: matches.length > 0 ? 'auto' : 200
                        }}>
                            {listLoading && <LinearProgress sx={{position: 'absolute', top: 0, left: 0, right: 0}}/>}
                            <Table size="small">
                                <TableHead sx={{bgcolor: '#fafafa'}}>
                                    <TableRow>
                                        <TableCell sx={{fontWeight: 'bold'}}>№</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>Наименование</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>АГСК-3</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>ЕНС ТРУ</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>Ед. изм.</TableCell>
                                        <TableCell sx={{fontWeight: 'bold', textAlign: 'right'}}>Кол-во</TableCell>
                                        <TableCell sx={{fontWeight: 'bold', textAlign: 'right'}}>Цена</TableCell>
                                        <TableCell sx={{fontWeight: 'bold', textAlign: 'right'}}>Сумма</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>Тип</TableCell>
                                        <TableCell sx={{fontWeight: 'bold'}}>Позиция</TableCell>
                                        <TableCell align="right" sx={{fontWeight: 'bold'}}>Действие</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {matches.length === 0 && !listLoading && (
                                        <TableRow>
                                            <TableCell colSpan={11} align="center" sx={{py: 6, borderBottom: 'none'}}>
                                                {onlyUnmatched ? (
                                                    <Box sx={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5}}>
                                                        <CheckCircleIcon sx={{fontSize: 48, color: 'success.main'}}/>
                                                        <Typography variant="subtitle1" fontWeight={600} color="text.primary">
                                                            Все позиции обработаны
                                                        </Typography>
                                                        <Typography variant="body2" color="text.secondary" sx={{maxWidth: 460}}>
                                                            Нет несопоставленных позиций. Авто-сопоставленные и выбранные аналитиком позиции скрыты фильтром.
                                                        </Typography>
                                                        <Button
                                                            variant="contained" size="small"
                                                            onClick={() => { setOnlyUnmatched(false); setPage(1); }}
                                                            sx={{mt: 1, textTransform: 'none'}}
                                                        >
                                                            Показать все позиции
                                                        </Button>
                                                    </Box>
                                                ) : debouncedAgskSearch ? (
                                                    <Box sx={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1}}>
                                                        <SearchIcon sx={{fontSize: 40, color: 'text.disabled'}}/>
                                                        <Typography variant="body2" color="text.secondary">
                                                            По запросу «{debouncedAgskSearch}» ничего не найдено
                                                        </Typography>
                                                    </Box>
                                                ) : (
                                                    <Typography variant="body2" color="text.secondary" sx={{fontStyle: 'italic'}}>
                                                        В этом документе нет позиций
                                                    </Typography>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    )}
                                    {matches.map(m => (
                                        <TableRow key={m.item_id} hover>
                                            <TableCell>{m.position_number}</TableCell>
                                            <TableCell sx={{maxWidth: 450}}>
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
                                                        <Highlight text={m.name} search={debouncedAgskSearch}/>
                                                    </Typography>
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell sx={{fontFamily: 'monospace', fontSize: '0.8rem'}}>
                                                <Highlight text={m.code_sn} search={debouncedAgskSearch}/>
                                            </TableCell>
                                            <TableCell sx={{color: 'primary.main', fontWeight: 'bold'}}>
                                                <Box sx={{display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.25}}>
                                                    {(m.current_manual_matches?.length ?? 0) > 0 ? (
                                                        m.current_manual_matches!.map(mm => (
                                                            <Box key={mm.id} sx={{display: 'flex', alignItems: 'center', gap: 0.5}}>
                                                                <Typography sx={{fontSize: '0.8rem', fontWeight: 'bold',
                                                                    color: (mm.status === 'active' || (mm.status as string) === 'approved') ? 'primary.main' : '#ed6c02'}}>
                                                                    {mm.enstru_code}
                                                                </Typography>
                                                                {(mm.status === 'active' || (mm.status as string) === 'approved')
                                                                    ? <Chip label="✓" size="small" color="success" sx={{height: 16, fontSize: '0.6rem', '& .MuiChip-label': {px: 0.5}}}/>
                                                                    : mm.status === 'rejected'
                                                                        ? <Chip label="✗" size="small" color="error" sx={{height: 16, fontSize: '0.6rem', '& .MuiChip-label': {px: 0.5}}}/>
                                                                        : <Chip label="⏳" size="small" color="warning" sx={{height: 16, fontSize: '0.6rem', '& .MuiChip-label': {px: 0.5}}}/>
                                                                }
                                                            </Box>
                                                        ))
                                                    ) : (
                                                        <Box sx={{display: 'flex', alignItems: 'center', gap: 1}}>
                                                            {m.enstru_code || '—'}
                                                            {m.match_reason && (
                                                                <Tooltip title={m.match_reason}>
                                                                    <InfoIcon sx={{fontSize: 14, color: '#90a4ae', cursor: 'help'}}/>
                                                                </Tooltip>
                                                            )}
                                                        </Box>
                                                    )}
                                                </Box>
                                            </TableCell>
                                            <TableCell sx={{fontSize: '0.75rem', color: 'text.secondary'}}>
                                                {m.unit}
                                            </TableCell>
                                            <TableCell
                                                sx={{fontSize: '0.75rem', textAlign: 'right', fontFamily: 'monospace'}}>
                                                {m.volume?.toLocaleString('ru-RU', {maximumFractionDigits: 3})}
                                            </TableCell>
                                            <TableCell
                                                sx={{fontSize: '0.75rem', textAlign: 'right', fontFamily: 'monospace'}}>
                                                {m.price?.toLocaleString('ru-RU', {maximumFractionDigits: 2})}
                                            </TableCell>
                                            <TableCell sx={{
                                                fontSize: '0.75rem',
                                                textAlign: 'right',
                                                fontFamily: 'monospace',
                                                fontWeight: 600
                                            }}>
                                                {m.total_amount?.toLocaleString('ru-RU', {maximumFractionDigits: 2})}
                                            </TableCell>
                                            <TableCell>
                                                {(() => {
                                                    const st = getItemStatus(m);
                                                    return (
                                                        <Chip
                                                            label={st.label}
                                                            color={st.color}
                                                            size="small"
                                                            sx={{fontSize: '0.7rem'}}
                                                        />
                                                    );
                                                })()}
                                            </TableCell>
                                            <TableCell>
                                                {(() => {
                                                    const itype = m.item_type || 'GOODS';
                                                    const cfg: Record<string, { label: string; color: any }> = {
                                                        GOODS: {label: 'Товар', color: 'success'},
                                                        WORKS: {label: 'Работа', color: 'default'},
                                                        SERVICES: {label: 'Услуга', color: 'secondary'},
                                                        OTHER: {label: 'Прочее', color: 'default'},
                                                    };
                                                    const c = cfg[itype];
                                                    if (!c) return null; // BALANCE не показываем
                                                    return (
                                                        <Chip
                                                            label={c.label}
                                                            size="small"
                                                            variant="outlined"
                                                            color={c.color}
                                                            sx={{fontSize: '0.65rem', height: 20}}
                                                        />
                                                    );
                                                })()}
                                            </TableCell>
                                            <TableCell align="right">
                                                {(!m.item_type || m.item_type === 'GOODS') ? (
                                                    (() => {
                                                        // Для auto/auto_ktp кнопка — это ПРОСМОТР,
                                                        // выбор поставщика недоступен
                                                        const isAuto = m.match_type === 'auto' || m.match_type === 'auto_ktp';
                                                        return (
                                                            <Tooltip title={isAuto ? 'Просмотр (авто-сопоставление)' : 'Выбрать поставщика'}>
                                                                <IconButton size="small" onClick={() => openEditDialog(m)}
                                                                            sx={{bgcolor: isAuto ? '#e8f5e9' : '#f0f4f8'}}>
                                                                    {isAuto
                                                                        ? <VisibilityIcon fontSize="small" sx={{color: 'success.main'}}/>
                                                                        : <EditIcon fontSize="small"/>}
                                                                </IconButton>
                                                            </Tooltip>
                                                        );
                                                    })()
                                                ) : (
                                                    <Typography variant="caption" color="text.disabled"
                                                                sx={{pr: 1}}>—</Typography>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>

                        {/* Комментарий аналитика для заключения */}
                        {selectedDoc && (selectedDoc.status === 'ASSIGNED_TO_ANALYST' || selectedDoc.status === 'REJECTED_BY_DIRECTOR' || selectedDoc.status === 'ANALYST_WORKING' || selectedDoc.status === 'FOR_APPROVAL' || selectedDoc.status === 'APPROVED' || selectedDoc.status === 'COMPLETED' || selectedDoc.status === 'SENT') && (
                            <Paper sx={{
                                mt: 3,
                                p: 2,
                                borderRadius: 2,
                                border: '1px solid #e0e0e0',
                                borderLeft: '4px solid #1976d2'
                            }}>
                                <Typography variant="subtitle2" fontWeight="bold"
                                            sx={{mb: 1.5, display: 'flex', alignItems: 'center', gap: 1}}>
                                    <CommentIcon sx={{fontSize: 18, color: 'primary.main'}}/>
                                    Комментарий аналитика для заключения
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{mb: 1, display: 'block'}}>
                                    Этот комментарий включается в DOCX заключение и виден директору ДРВЦ
                                </Typography>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={3}
                                    placeholder="Введите дополнительный комментарий к заключению..."
                                    value={analystComment}
                                    onChange={(e) => setAnalystComment(e.target.value)}
                                    disabled={savingComment || (selectedDoc.status === 'APPROVED' || selectedDoc.status === 'COMPLETED' || selectedDoc.status === 'SENT')}
                                    sx={{mb: 1.5}}
                                />
                                {/* Показываем кнопку сохранения только аналитику, пока документ в работе */}
                                {(selectedDoc.status === 'ASSIGNED_TO_ANALYST' || selectedDoc.status === 'REJECTED_BY_DIRECTOR' || selectedDoc.status === 'ANALYST_WORKING' || selectedDoc.status === 'FOR_APPROVAL') && selectedDoc.assigned_to === currentUser?.id && (
                                    <Box sx={{display: 'flex', justifyContent: 'flex-end', gap: 1}}>
                                        <Button
                                            size="small"
                                            variant="contained"
                                            color="primary"
                                            onClick={handleSaveAnalystComment}
                                            disabled={savingComment}
                                            startIcon={savingComment ?
                                                <CircularProgress size={14} color="inherit"/> : null}
                                        >
                                            {savingComment ? 'Сохранение...' : 'Сохранить комментарий'}
                                        </Button>
                                    </Box>
                                )}
                                {/* Для директора и завершенных документов - только отображение инфо */}
                                {(selectedDoc.status === 'APPROVED' || selectedDoc.status === 'COMPLETED' || selectedDoc.status === 'SENT' || (selectedDoc.status === 'FOR_APPROVAL' && selectedDoc.assigned_to !== currentUser?.id)) && (
                                    <Box sx={{display: 'flex', justifyContent: 'flex-end'}}>
                                        <Typography variant="caption" color="text.secondary">
                                            {selectedDoc.analyst_comment ? 'Комментарий будет включен в заключение' : 'Аналитик не добавил комментарий'}
                                        </Typography>
                                    </Box>
                                )}
                            </Paper>
                        )}

                        <Box sx={{mt: 2, display: 'flex', justifyContent: 'center'}}>
                            <Pagination size="small" count={Math.ceil(totalCount / 50)} page={page}
                                        onChange={(_, v) => setPage(v)} color="primary"/>
                        </Box>
                    </Box>
                )}

                {activeTab === (selectedDoc ? 2 : 1) && (
                    <Box>
                        {/* Заголовок */}
                        <Box sx={{display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5, flexWrap: 'wrap'}}>
                            <Typography variant="subtitle1" fontWeight="bold" color="primary" sx={{flex: 1}}>
                                Библиотека сопоставлений АГСК → ЕНСТРУ
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Всего: <b>{matchesLibraryTotal}</b>
                                {matchesLibraryTotal > LIBRARY_PAGE_SIZE && (
                                    <> · стр. {matchesLibraryPage} из {Math.ceil(matchesLibraryTotal / LIBRARY_PAGE_SIZE)}</>
                                )}
                            </Typography>
                            <Button size="small" variant="outlined" startIcon={<RefreshIcon/>}
                                    onClick={loadMatchesLibrary} disabled={matchesLoading} sx={{textTransform: 'none'}}>
                                Обновить
                            </Button>
                            <Button size="small" variant="contained" color="primary"
                                    onClick={() => setCreateMatchOpen(true)}
                                    sx={{textTransform: 'none', fontWeight: 'bold'}}>
                                + Создать связку
                            </Button>
                        </Box>

                        {/* Панель фильтров */}
                        <Paper sx={{p: 1.5, mb: 2, display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', borderRadius: 2, border: '1px solid #e0e0e0'}} elevation={0}>
                            <TextField
                                size="small"
                                placeholder="Поиск по коду АГСК или ЕНСТРУ…"
                                value={librarySearch}
                                onChange={e => { setLibrarySearch(e.target.value); setMatchesLibraryPage(1); }}
                                InputProps={{startAdornment: <InputAdornment position="start"><SearchIcon sx={{fontSize: 16}}/></InputAdornment>}}
                                sx={{width: 260, '& .MuiInputBase-root': {fontSize: '0.82rem'}}}
                            />
                            <Divider orientation="vertical" flexItem/>
                            <Typography variant="caption" color="text.secondary" sx={{whiteSpace: 'nowrap'}}>Статус:</Typography>
                            <ToggleButtonGroup size="small" value={libraryStatusFilter} exclusive
                                onChange={(_, v) => { if (v) { setLibraryStatusFilter(v); setMatchesLibraryPage(1); } }}
                                sx={{bgcolor: 'white'}}>
                                <ToggleButton value="all" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem'}}>Все</ToggleButton>
                                <ToggleButton value="pending" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem', color: 'warning.main'}}>Ожидает</ToggleButton>
                                <ToggleButton value="approved" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem', color: 'success.main'}}>Утверждено</ToggleButton>
                                <ToggleButton value="rejected" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem', color: 'error.main'}}>Отклонено</ToggleButton>
                            </ToggleButtonGroup>
                            <Divider orientation="vertical" flexItem/>
                            <Typography variant="caption" color="text.secondary" sx={{whiteSpace: 'nowrap'}}>Дата:</Typography>
                            <ToggleButtonGroup size="small" value={matchDateFilter} exclusive
                                onChange={(_, v) => { if (v) { setMatchDateFilter(v); setMatchesLibraryPage(1); } }} sx={{bgcolor: 'white'}}>
                                <ToggleButton value="all" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem'}}>Все</ToggleButton>
                                <ToggleButton value="today" sx={{px: 1.5, textTransform: 'none', fontSize: '0.75rem'}}>Сегодня</ToggleButton>
                            </ToggleButtonGroup>
                            {(isAnalystManager || isDirector) && (<>
                                <Divider orientation="vertical" flexItem/>
                                <Typography variant="caption" color="text.secondary" sx={{whiteSpace: 'nowrap'}}>Аналитик:</Typography>
                                <FormControl size="small" sx={{minWidth: 180}}>
                                    <Select
                                        value={libraryAnalystFilter ?? ''}
                                        onChange={e => { const v = e.target.value; setLibraryAnalystFilter(v === '' || v === 0 ? null : Number(v)); setMatchesLibraryPage(1); }}
                                        displayEmpty
                                        sx={{fontSize: '0.82rem', bgcolor: 'white'}}
                                    >
                                        <MenuItem value=""><em style={{fontStyle: 'normal', color: '#999'}}>Все аналитики</em></MenuItem>
                                        {analysts.map(a => (
                                            <MenuItem key={a.id} value={a.id} sx={{fontSize: '0.82rem'}}>
                                                {a.full_name}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </>)}
                        </Paper>

                        {/* Группированный вид: один блок = один АГСК со всеми ЕНСТРУ */}
                        {matchesLoading && <LinearProgress sx={{mb: 1}}/>}

                        {matchesLibrary.length === 0 && !matchesLoading && (
                            <Paper sx={{p: 4, textAlign: 'center', borderRadius: 2, border: '1px solid #e0e0e0'}}>
                                <Typography variant="body2" color="text.secondary">Нет сопоставлений</Typography>
                            </Paper>
                        )}

                        <Stack spacing={1.5}>
                            {(() => {
                                // Группируем по agsk_code
                                const groups: Record<string, AgskEnstruMatchItem[]> = {};
                                for (const m of matchesLibrary) {
                                    if (!groups[m.agsk_code]) groups[m.agsk_code] = [];
                                    groups[m.agsk_code].push(m);
                                }
                                return Object.entries(groups).map(([agskCode, items]) => {
                                    const agskName = items[0]?.agsk_full_name;
                                    const pendingCount = items.filter(i => i.status === 'pending').length;
                                    const approvedCount = items.filter(i => i.status === 'approved').length;
                                    const isGroupExpanded = expandedGroups.has(agskCode);
                                    return (
                                        <Paper key={agskCode} elevation={0} sx={{border: '1px solid #e0e0e0', borderRadius: 2, overflow: 'hidden'}}>
                                            {/* Заголовок группы АГСК */}
                                            <Box
                                                onClick={() => setExpandedGroups(prev => {
                                                    const next = new Set(prev);
                                                    if (next.has(agskCode)) next.delete(agskCode); else next.add(agskCode);
                                                    return next;
                                                })}
                                                sx={{
                                                    px: 2, py: 1.25, display: 'flex', alignItems: 'center', gap: 1.5,
                                                    bgcolor: '#f5f7fa', cursor: 'pointer',
                                                    borderBottom: isGroupExpanded ? '1px solid #e0e0e0' : 'none',
                                                    '&:hover': {bgcolor: '#eef1f6'},
                                                }}
                                            >
                                                <AgskIcon sx={{color: '#1565c0', fontSize: 18, flexShrink: 0}}/>
                                                <Box sx={{flex: 1, minWidth: 0}}>
                                                    <Typography sx={{fontFamily: 'monospace', fontWeight: 'bold', fontSize: '0.85rem', color: '#1565c0', lineHeight: 1.2}}>
                                                        {agskCode}
                                                    </Typography>
                                                    {agskName && (
                                                        <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.3, mt: 0.25, wordBreak: 'break-word'}}>
                                                            {agskName}
                                                        </Typography>
                                                    )}
                                                </Box>
                                                <Stack direction="row" spacing={0.5} alignItems="center" sx={{flexShrink: 0}}>
                                                    {pendingCount > 0 && (
                                                        <Chip size="small" label={`${pendingCount} ожидает`} color="warning" sx={{fontSize: '0.65rem', height: 20}}/>
                                                    )}
                                                    {approvedCount > 0 && (
                                                        <Chip size="small" label={`${approvedCount} утв.`} color="success" variant="outlined" sx={{fontSize: '0.65rem', height: 20}}/>
                                                    )}
                                                    <Chip size="small" label={`${items.length} ЕНСТРУ`} variant="outlined" sx={{fontSize: '0.65rem', height: 20}}/>
                                                    <IconButton size="small" sx={{p: 0.25}}>
                                                        {isGroupExpanded ? <ExpandLessIcon fontSize="small"/> : <ExpandMoreIcon fontSize="small"/>}
                                                    </IconButton>
                                                </Stack>
                                            </Box>

                                            {/* Список ЕНСТРУ сопоставлений */}
                                            {isGroupExpanded && (
                                                <Box>
                                                    {items.map((m, idx) => (
                                                        <Box key={m.id} sx={{
                                                            px: 2, py: 1.25,
                                                            borderBottom: idx < items.length - 1 ? '1px solid #f0f0f0' : 'none',
                                                            bgcolor: m.status === 'approved' ? '#f1f8e9' : m.status === 'rejected' ? '#fff8f8' : 'white',
                                                            display: 'flex', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap',
                                                        }}>
                                                            {/* Статус */}
                                                            <Box sx={{width: 80, flexShrink: 0, pt: 0.25}}>
                                                                <Chip
                                                                    size="small"
                                                                    label={m.status === 'approved' ? 'Утв.' : m.status === 'pending' ? 'Ожидает' : 'Откл.'}
                                                                    color={m.status === 'approved' ? 'success' : m.status === 'pending' ? 'warning' : 'error'}
                                                                    variant={m.status === 'pending' ? 'filled' : 'outlined'}
                                                                    sx={{fontSize: '0.65rem', height: 20}}
                                                                />
                                                            </Box>

                                                            {/* ЕНСТРУ */}
                                                            <Box sx={{flex: 1, minWidth: 180}}>
                                                                <Typography sx={{fontSize: '0.82rem', fontWeight: 'bold', color: 'primary.main', lineHeight: 1.2}}>
                                                                    {m.enstru_code}
                                                                </Typography>
                                                                {m.enstru_name_rus && (
                                                                    <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.35, mt: 0.25, wordBreak: 'break-word'}}>
                                                                        {m.enstru_name_rus}
                                                                    </Typography>
                                                                )}
                                                                {m.enstru_detail_rus && (
                                                                    <Typography variant="caption" color="text.disabled" sx={{display: 'block', lineHeight: 1.3, fontStyle: 'italic', wordBreak: 'break-word'}}>
                                                                        {m.enstru_detail_rus}
                                                                    </Typography>
                                                                )}
                                                                {m.enstru_standard && (
                                                                    <Typography variant="caption" sx={{display: 'block', color: '#78909c', fontSize: '0.6rem'}}>
                                                                        {m.enstru_standard}
                                                                    </Typography>
                                                                )}
                                                            </Box>

                                                            {/* Аналитик + дата */}
                                                            <Box sx={{width: 150, flexShrink: 0}}>
                                                                <Typography variant="caption" sx={{display: 'flex', alignItems: 'center', gap: 0.5}}>
                                                                    <PersonIcon sx={{fontSize: 12, color: 'text.secondary'}}/>
                                                                    {m.analyst_name || '—'}
                                                                </Typography>
                                                                {m.approved_by_name && (
                                                                    <Typography variant="caption" color="success.main" sx={{display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.65rem'}}>
                                                                        <CheckCircleIcon sx={{fontSize: 11}}/>
                                                                        {m.approved_by_name}
                                                                    </Typography>
                                                                )}
                                                                <Typography variant="caption" color="text.secondary" sx={{display: 'block', fontSize: '0.65rem', mt: 0.25}}>
                                                                    {m.created_at ? new Date(m.created_at).toLocaleString('ru-RU', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'}) : '—'}
                                                                </Typography>
                                                            </Box>

                                                            {/* Кнопки действий (только для менеджера) */}
                                                            {isAnalystManager && (
                                                                <Box sx={{width: 180, flexShrink: 0, display: 'flex', justifyContent: 'flex-end', alignItems: 'center'}}>
                                                                    {m.status === 'pending' ? (
                                                                        <Stack direction="row" spacing={0.5}>
                                                                            <Button
                                                                                size="small" variant="contained" color="success"
                                                                                disabled={approvingId === m.id}
                                                                                onClick={() => approveMatch(m.id)}
                                                                                sx={{textTransform: 'none', fontSize: '0.7rem', py: 0.25, minWidth: 80}}
                                                                                startIcon={approvingId === m.id ? <CircularProgress size={12} color="inherit"/> : null}
                                                                            >
                                                                                Утвердить
                                                                            </Button>
                                                                            <Button
                                                                                size="small" variant="outlined" color="error"
                                                                                disabled={approvingId === m.id}
                                                                                onClick={() => rejectMatch(m.id)}
                                                                                sx={{textTransform: 'none', fontSize: '0.7rem', py: 0.25, minWidth: 80}}
                                                                            >
                                                                                Отклонить
                                                                            </Button>
                                                                        </Stack>
                                                                    ) : (
                                                                        <Typography variant="caption" color="text.disabled">—</Typography>
                                                                    )}
                                                                </Box>
                                                            )}
                                                        </Box>
                                                    ))}
                                                </Box>
                                            )}
                                        </Paper>
                                    );
                                });
                            })()}
                        </Stack>

                        {/* Пагинация */}
                        {matchesLibraryTotal > LIBRARY_PAGE_SIZE && (
                            <Box sx={{display: 'flex', justifyContent: 'center', mt: 2}}>
                                <Pagination
                                    count={Math.ceil(matchesLibraryTotal / LIBRARY_PAGE_SIZE)}
                                    page={matchesLibraryPage}
                                    onChange={(_, p) => setMatchesLibraryPage(p)}
                                    color="primary"
                                    size="small"
                                    showFirstButton
                                    showLastButton
                                    disabled={matchesLoading}
                                />
                            </Box>
                        )}
                    </Box>
                )}

                {/* --- ДИАЛОГ СОЗДАНИЯ СВЯЗКИ АГСК→ЕНСТРУ --- */}
                <Dialog open={createMatchOpen} onClose={() => { if (!creatingMatch) { setCreateMatchOpen(false); setNewMatchAgsk(null); setNewMatchEnstruList([]); setAgskInputVal(''); setEnstruInputVal(''); setExistingAgskMatches([]); } }}
                        maxWidth="md" fullWidth PaperProps={{sx: {borderRadius: 2, minHeight: 460}}}>
                    <DialogTitle sx={{pb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                        <Typography fontWeight="bold" fontSize="1rem">Создать связку АГСК → ЕНСТРУ</Typography>
                        <IconButton size="small" onClick={() => setCreateMatchOpen(false)} disabled={creatingMatch}>
                            <CloseIcon fontSize="small"/>
                        </IconButton>
                    </DialogTitle>
                    <DialogContent dividers sx={{pt: 2}}>
                        <Typography variant="caption" color="text.secondary" sx={{display: 'block', mb: 2}}>
                            Выберите АГСК и ЕНСТРУ для сопоставления. После создания связка будет отправлена на утверждение менеджеру.
                        </Typography>

                        <Box sx={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2.5, alignItems: 'start'}}>
                            {/* ── Левая колонка: АГСК ── */}
                            <Box>
                                <Box sx={{display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75}}>
                                    <AgskIcon sx={{fontSize: 16, color: '#1565c0'}}/>
                                    <Typography variant="caption" fontWeight="bold" color="#1565c0">АГСК — код товара</Typography>
                                </Box>
                                <TextField
                                    fullWidth size="small" placeholder="Код или название…"
                                    value={agskInputVal}
                                    onChange={e => { setAgskInputVal(e.target.value); if (newMatchAgsk) setNewMatchAgsk(null); }}
                                    InputProps={{
                                        endAdornment: agskSearchLoading ? <InputAdornment position="end"><CircularProgress size={14}/></InputAdornment> : null,
                                    }}
                                    sx={{mb: 0.5}}
                                />
                                {agskOptions.length > 0 && !newMatchAgsk && (
                                    <Paper elevation={3} sx={{maxHeight: 260, overflow: 'auto', border: '1px solid #e0e0e0', borderRadius: 1}}>
                                        {agskOptions.map(opt => {
                                            const q = agskInputVal.toLowerCase();
                                            const highlight = (text: string) => {
                                                if (!q) return <>{text}</>;
                                                const idx = text.toLowerCase().indexOf(q);
                                                if (idx === -1) return <>{text}</>;
                                                return <>{text.slice(0, idx)}<mark style={{background: '#fff176', borderRadius: 2, padding: '0 1px'}}>{text.slice(idx, idx + q.length)}</mark>{text.slice(idx + q.length)}</>;
                                            };
                                            return (
                                                <Box key={opt.id}
                                                    onClick={() => { setNewMatchAgsk({code: opt.code, full_name: opt.full_name || opt.name_ru}); setAgskInputVal(opt.code); setAgskOptions([]); }}
                                                    sx={{px: 1.5, py: 1, cursor: 'pointer', '&:hover': {bgcolor: '#f5f5f5'}, borderBottom: '1px solid #f0f0f0'}}>
                                                    <Typography sx={{fontFamily: 'monospace', fontSize: '0.82rem', fontWeight: 'bold', color: '#1565c0'}}>
                                                        {highlight(opt.code)}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.35, wordBreak: 'break-word'}}>
                                                        {highlight(opt.full_name || opt.name_ru)}
                                                    </Typography>
                                                </Box>
                                            );
                                        })}
                                    </Paper>
                                )}
                                {newMatchAgsk && (
                                    <Paper sx={{p: 1.25, mt: 0.5, bgcolor: '#e3f2fd', border: '1px solid #90caf9', borderRadius: 1, display: 'flex', gap: 1, alignItems: 'flex-start'}}>
                                        <CheckCircleIcon sx={{color: '#1565c0', fontSize: 18, mt: 0.1, flexShrink: 0}}/>
                                        <Box sx={{flex: 1, minWidth: 0}}>
                                            <Typography sx={{fontFamily: 'monospace', fontSize: '0.85rem', fontWeight: 'bold', color: '#1565c0'}}>{newMatchAgsk.code}</Typography>
                                            <Typography variant="caption" color="text.secondary" sx={{wordBreak: 'break-word'}}>{newMatchAgsk.full_name}</Typography>
                                        </Box>
                                        <IconButton size="small" sx={{p: 0.25, flexShrink: 0}} onClick={() => { setNewMatchAgsk(null); setAgskInputVal(''); }}>
                                            <CloseIcon sx={{fontSize: 14}}/>
                                        </IconButton>
                                    </Paper>
                                )}
                            </Box>

                            {/* ── Правая колонка: ЕНСТРУ ── */}
                            <Box>
                                <Box sx={{display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75}}>
                                    <CategoryIcon sx={{fontSize: 16, color: 'primary.main'}}/>
                                    <Typography variant="caption" fontWeight="bold" color="primary.main">ЕНСТРУ — код закупки</Typography>
                                    {existingAgskLoading && <CircularProgress size={12} sx={{ml: 0.5}}/>}
                                </Box>

                                {/* Уже существующие связки для этого АГСК */}
                                {!newMatchAgsk && (
                                    <Paper elevation={0} sx={{p: 1.5, border: '1px dashed #ddd', borderRadius: 1, mb: 1, textAlign: 'center'}}>
                                        <Typography variant="caption" color="text.disabled">
                                            Сначала выберите АГСК слева
                                        </Typography>
                                    </Paper>
                                )}
                                {newMatchAgsk && existingAgskMatches.length > 0 && (
                                    <Paper elevation={0} sx={{border: '1px solid #e0e0e0', borderRadius: 1, mb: 1.5, overflow: 'hidden'}}>
                                        <Box sx={{px: 1.25, py: 0.75, bgcolor: '#f5f5f5', borderBottom: '1px solid #e0e0e0'}}>
                                            <Typography variant="caption" fontWeight="bold" color="text.secondary">
                                                Уже в библиотеке ({existingAgskMatches.length})
                                            </Typography>
                                        </Box>
                                        <Box sx={{maxHeight: 160, overflow: 'auto'}}>
                                            {existingAgskMatches.map(ex => {
                                                const isRejected = ex.status === 'rejected';
                                                const isActive = ex.status === 'pending' || ex.status === 'approved';
                                                const alreadyInList = newMatchEnstruList.some(e => e.code === ex.enstru_code);
                                                return (
                                                    <Box key={ex.id} sx={{
                                                        px: 1.25, py: 0.75,
                                                        borderBottom: '1px solid #f0f0f0',
                                                        display: 'flex', alignItems: 'flex-start', gap: 1,
                                                        bgcolor: isRejected ? '#fff8f8' : isActive ? '#f9fffe' : 'white',
                                                        opacity: isActive && !alreadyInList ? 0.85 : 1,
                                                    }}>
                                                        <Box sx={{flex: 1, minWidth: 0}}>
                                                            <Typography sx={{fontSize: '0.78rem', fontWeight: 'bold',
                                                                color: ex.status === 'approved' ? 'success.main' : ex.status === 'pending' ? 'warning.dark' : 'error.main',
                                                                lineHeight: 1.2}}>
                                                                {ex.enstru_code}
                                                            </Typography>
                                                            {ex.enstru_name_rus && (
                                                                <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.3, wordBreak: 'break-word'}}>
                                                                    {ex.enstru_name_rus}
                                                                </Typography>
                                                            )}
                                                            {ex.enstru_detail_rus && (
                                                                <Typography variant="caption" color="text.disabled" sx={{display: 'block', lineHeight: 1.3, fontStyle: 'italic', wordBreak: 'break-word'}}>
                                                                    {ex.enstru_detail_rus}
                                                                </Typography>
                                                            )}
                                                        </Box>
                                                        <Box sx={{flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.25}}>
                                                            <Chip size="small"
                                                                label={ex.status === 'approved' ? 'Утв.' : ex.status === 'pending' ? 'Ожидает' : 'Откл.'}
                                                                color={ex.status === 'approved' ? 'success' : ex.status === 'pending' ? 'warning' : 'error'}
                                                                variant="outlined"
                                                                sx={{fontSize: '0.6rem', height: 18}}
                                                            />
                                                            {isRejected && !alreadyInList && (
                                                                <Typography
                                                                    variant="caption"
                                                                    sx={{color: 'primary.main', cursor: 'pointer', fontSize: '0.65rem', textDecoration: 'underline', mt: 0.25}}
                                                                    onClick={() => {
                                                                        setNewMatchEnstruList(prev => [...prev, {code: ex.enstru_code, name_rus: ex.enstru_name_rus || ex.enstru_code}]);
                                                                    }}
                                                                >
                                                                    + Повторить
                                                                </Typography>
                                                            )}
                                                            {alreadyInList && (
                                                                <Typography variant="caption" color="success.main" sx={{fontSize: '0.65rem'}}>
                                                                    ✓ добавлен
                                                                </Typography>
                                                            )}
                                                        </Box>
                                                    </Box>
                                                );
                                            })}
                                        </Box>
                                    </Paper>
                                )}
                                {newMatchAgsk && existingAgskMatches.length === 0 && !existingAgskLoading && (
                                    <Paper elevation={0} sx={{px: 1.25, py: 0.75, border: '1px solid #e8f5e9', borderRadius: 1, mb: 1.5, bgcolor: '#f9fffe'}}>
                                        <Typography variant="caption" color="success.main">
                                            Нет существующих связок — можно добавить новые
                                        </Typography>
                                    </Paper>
                                )}
                                <TextField
                                    fullWidth size="small" placeholder="Код или название…"
                                    value={enstrupInputVal}
                                    onChange={e => { setEnstruInputVal(e.target.value); }}
                                    InputProps={{
                                        endAdornment: enstrupSearchLoading ? <InputAdornment position="end"><CircularProgress size={14}/></InputAdornment> : null,
                                    }}
                                    sx={{mb: 0.5}}
                                />
                                {enstrupOptions.length > 0 && (
                                    <Paper elevation={3} sx={{maxHeight: 220, overflow: 'auto', border: '1px solid #e0e0e0', borderRadius: 1, mb: 1}}>
                                        {enstrupOptions.map(opt => {
                                            const alreadyAdded = newMatchEnstruList.some(e => e.code === opt.code);
                                            const existingActive = existingAgskMatches.find(ex => ex.enstru_code === opt.code && (ex.status === 'pending' || ex.status === 'approved'));
                                            const isBlocked = alreadyAdded || !!existingActive;
                                            const q = enstrupInputVal.toLowerCase();
                                            const highlight = (text: string) => {
                                                if (!q) return <>{text}</>;
                                                const idx = text.toLowerCase().indexOf(q);
                                                if (idx === -1) return <>{text}</>;
                                                return <>{text.slice(0, idx)}<mark style={{background: '#fff176', borderRadius: 2, padding: '0 1px'}}>{text.slice(idx, idx + q.length)}</mark>{text.slice(idx + q.length)}</>;
                                            };
                                            return (
                                                <Box key={opt.id}
                                                    onClick={() => {
                                                        if (!isBlocked) {
                                                            setNewMatchEnstruList(prev => [...prev, {code: opt.code, name_rus: opt.name_rus}]);
                                                            setEnstruInputVal('');
                                                            setEnstruOptions([]);
                                                        }
                                                    }}
                                                    sx={{
                                                        px: 1.5, py: 1,
                                                        cursor: isBlocked ? 'default' : 'pointer',
                                                        bgcolor: alreadyAdded ? '#f1f8e9' : existingActive ? '#fffde7' : 'white',
                                                        '&:hover': {bgcolor: isBlocked ? (alreadyAdded ? '#f1f8e9' : '#fffde7') : '#f5f5f5'},
                                                        borderBottom: '1px solid #f0f0f0',
                                                        display: 'flex', alignItems: 'flex-start', gap: 1,
                                                    }}>
                                                    <Box sx={{flex: 1, minWidth: 0}}>
                                                        <Typography sx={{fontSize: '0.82rem', fontWeight: 'bold',
                                                            color: alreadyAdded ? 'success.main' : existingActive ? 'warning.dark' : 'primary.main'}}>
                                                            {highlight(opt.code)}
                                                        </Typography>
                                                        <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.35, wordBreak: 'break-word'}}>
                                                            {highlight(opt.name_rus)}
                                                        </Typography>
                                                        {opt.detail_rus && (
                                                            <Typography variant="caption" color="text.disabled" sx={{display: 'block', fontStyle: 'italic', lineHeight: 1.3, wordBreak: 'break-word'}}>
                                                                {highlight(opt.detail_rus)}
                                                            </Typography>
                                                        )}
                                                        {existingActive && (
                                                            <Typography variant="caption" sx={{color: 'warning.dark', fontSize: '0.65rem'}}>
                                                                уже {existingActive.status === 'approved' ? 'утверждена' : 'на рассмотрении'}
                                                            </Typography>
                                                        )}
                                                    </Box>
                                                    {alreadyAdded && <CheckCircleIcon sx={{fontSize: 16, color: 'success.main', flexShrink: 0, mt: 0.25}}/>}
                                                    {existingActive && !alreadyAdded && <InfoIcon sx={{fontSize: 16, color: 'warning.main', flexShrink: 0, mt: 0.25}}/>}
                                                </Box>
                                            );
                                        })}
                                    </Paper>
                                )}

                                {/* Выбранные ЕНСТРУ — список чипов */}
                                {newMatchEnstruList.length > 0 && (
                                    <Paper sx={{p: 1, border: '1px solid #a5d6a7', borderRadius: 1, bgcolor: '#f9fffe'}} elevation={0}>
                                        <Typography variant="caption" fontWeight="bold" color="success.main" sx={{display: 'block', mb: 0.75}}>
                                            Выбрано ({newMatchEnstruList.length}):
                                        </Typography>
                                        <Stack spacing={0.5}>
                                            {newMatchEnstruList.map(e => (
                                                <Box key={e.code} sx={{display: 'flex', alignItems: 'flex-start', gap: 0.5, bgcolor: '#e8f5e9', borderRadius: 1, px: 1, py: 0.5}}>
                                                    <Box sx={{flex: 1, minWidth: 0}}>
                                                        <Typography sx={{fontSize: '0.78rem', fontWeight: 'bold', color: 'primary.main', lineHeight: 1.2}}>{e.code}</Typography>
                                                        <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.3, wordBreak: 'break-word'}}>{e.name_rus}</Typography>
                                                    </Box>
                                                    <IconButton size="small" sx={{p: 0.1, flexShrink: 0, mt: 0.1}}
                                                        onClick={() => setNewMatchEnstruList(prev => prev.filter(x => x.code !== e.code))}>
                                                        <CloseIcon sx={{fontSize: 13}}/>
                                                    </IconButton>
                                                </Box>
                                            ))}
                                        </Stack>
                                    </Paper>
                                )}
                            </Box>
                        </Box>
                    </DialogContent>
                    <DialogActions sx={{px: 2, py: 1.5}}>
                        <Button onClick={() => { setCreateMatchOpen(false); setNewMatchAgsk(null); setNewMatchEnstruList([]); setAgskInputVal(''); setEnstruInputVal(''); setExistingAgskMatches([]); }} disabled={creatingMatch} sx={{textTransform: 'none'}}>
                            Отмена
                        </Button>
                        <Button
                            variant="contained" color="primary"
                            disabled={!newMatchAgsk || newMatchEnstruList.length === 0 || creatingMatch}
                            onClick={handleCreateMatch}
                            startIcon={creatingMatch ? <CircularProgress size={14} color="inherit"/> : null}
                            sx={{textTransform: 'none', fontWeight: 'bold'}}
                        >
                            Создать и отправить на утверждение
                        </Button>
                    </DialogActions>
                </Dialog>

                {/* --- ДИАЛОГИ ДИРЕКТОРА --- */}
                <AssignDialog
                    open={assignDialogOpen}
                    onClose={() => setAssignDialogOpen(false)}
                    analysts={analysts}
                    onSubmit={handleAssignAnalyst}
                    loading={actionLoading}
                />
                <RejectDialog
                    open={rejectDialogOpen}
                    onClose={() => setRejectDialogOpen(false)}
                    onSubmit={handleReject}
                    loading={actionLoading}
                />
                <DelegateDialog
                    open={delegateDialogOpen}
                    onClose={() => setDelegateDialogOpen(false)}
                    analysts={analysts}
                    onSubmit={handleDelegate}
                    loading={actionLoading}
                />
                <UploadDialog
                    open={uploadDialogOpen}
                    onClose={() => setUploadDialogOpen(false)}
                    onSubmit={handleUploadTest}
                    loading={uploading}
                />

                <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}
                        maxWidth="xl" fullWidth
                        PaperProps={{sx: {height: '85vh', borderRadius: 2, overflow: 'hidden'}}}>

                    {/* Read-only режим: auto/auto_ktp — АГСК напрямую сопоставлен с реестром КТП,
                        ручной выбор поставщика не нужен, аналитик только смотрит результат. */}
                    <DialogTitle sx={{
                        borderBottom: '1px solid #eee', py: 1.5, px: 2,
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        bgcolor: (editingMatch?.match_type === 'auto' || editingMatch?.match_type === 'auto_ktp') ? '#e8f5e9' : 'inherit',
                    }}>
                        <Box sx={{minWidth: 0, flex: 1, display: 'flex', alignItems: 'center', gap: 1}}>
                            {(editingMatch?.match_type === 'auto' || editingMatch?.match_type === 'auto_ktp') && (
                                <Chip
                                    icon={<VisibilityIcon sx={{fontSize: 14}}/>}
                                    label="Просмотр (авто)"
                                    size="small"
                                    color="success"
                                    sx={{fontSize: '0.7rem', height: 22, fontWeight: 'bold'}}
                                />
                            )}
                            <Typography variant="subtitle1" fontWeight="bold" color="primary">
                                {editingMatch?.name} — {editingMatch?.code_sn}
                            </Typography>
                        </Box>
                        <IconButton size="small" onClick={() => setEditDialogOpen(false)}>
                            <CloseIcon/>
                        </IconButton>
                    </DialogTitle>

                    <DialogContent sx={{p: 0, display: 'flex', bgcolor: '#f8f9fa', overflow: 'hidden', flex: 1}}>
                        {editingMatch && (
                            <Box sx={{display: 'flex', width: '100%', height: '100%', overflow: 'hidden'}}>

                                <Box sx={{
                                    width: 320, minWidth: 320, bgcolor: 'white',
                                    borderRight: '1px solid #e0e0e0',
                                    display: 'flex', flexDirection: 'column', overflow: 'hidden'
                                }}>
                                    <Box sx={{p: 1.5, bgcolor: '#f0f7ff', borderBottom: '1px solid #e3f2fd'}}>
                                        <Typography variant="caption" fontWeight="bold" color="primary">
                                            ТЕКУЩЕЕ СОПОСТАВЛЕНИЕ
                                        </Typography>
                                    </Box>

                                    {/* Отметка аналитика - Нет в реестре КТП (скрыта в режиме просмотра) */}
                                    {!isReadOnlyDialog && (
                                        <Box sx={{p: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: '#fff3e0'}}>
                                            <FormControlLabel
                                                control={
                                                    <Switch
                                                        size="small"
                                                        checked={editingMatch?.not_in_ktp_registry || false}
                                                        onChange={(e) => {
                                                            const id = editingMatch?.item_id || editingMatch?.id;
                                                            if (id) saveNotInKtpRegistry(id, e.target.checked);
                                                        }}
                                                        color="warning"
                                                    />
                                                }
                                                label={
                                                    <Typography variant="caption"
                                                                color={editingMatch?.not_in_ktp_registry ? 'warning.main' : 'text.secondary'}>
                                                        Нет в реестре КТП
                                                    </Typography>
                                                }
                                            />
                                            {editingMatch?.not_in_ktp_registry && (
                                                <Typography variant="caption" color="text.secondary"
                                                            sx={{display: 'block', mt: 0.5, fontStyle: 'italic'}}>
                                                    Сопоставление сброшено
                                                </Typography>
                                            )}
                                        </Box>
                                    )}

                                    <Box sx={{flexGrow: 1, overflowY: 'auto', p: 1.5}}>
                                        {/* Подсказка из библиотеки / авто — нет выбора поставщика */}
                                        {editingMatch?.enstru_code && !(editingMatch?.current_manual_matches?.length) && (
                                            <Paper elevation={0} sx={{
                                                p: 1.5, mb: 1.5,
                                                border: editingMatch.match_type === 'auto' || editingMatch.match_type === 'auto_ktp'
                                                    ? '1px solid #90caf9' : '1px solid #90caf9',
                                                borderRadius: 2,
                                                bgcolor: editingMatch.match_type === 'auto' || editingMatch.match_type === 'auto_ktp'
                                                    ? '#e8eaf6' : '#e3f2fd',
                                            }}>
                                                <Box sx={{display: 'flex', alignItems: 'center', gap: 1, mb: 0.5}}>
                                                    <Chip
                                                        label={editingMatch.match_type === 'auto' || editingMatch.match_type === 'auto_ktp'
                                                            ? '🤖 Авто' : '💡 Подсказка'}
                                                        size="small"
                                                        color={editingMatch.match_type === 'auto' || editingMatch.match_type === 'auto_ktp'
                                                            ? 'primary' : 'info'}
                                                        sx={{height: 18, fontSize: '0.6rem'}}
                                                    />
                                                    <Typography variant="caption" fontWeight="bold" color="primary">
                                                        {editingMatch.enstru_code}
                                                    </Typography>
                                                </Box>
                                                <Typography sx={{fontSize: '0.65rem', color: 'text.secondary'}}>
                                                    Поставщик не выбран. Найдите в реестре КТП справа →
                                                </Typography>
                                            </Paper>
                                        )}

                                        {/* Выборы поставщиков: active = выбран, pending = ожидает одобрения */}
                                        {(editingMatch?.current_manual_matches?.length ?? 0) > 0 ? (
                                            <Box sx={{display: 'flex', flexDirection: 'column', gap: 0.75, mb: 1}}>
                                                {editingMatch!.current_manual_matches!.map(mm => {
                                                    const isActive = mm.status === 'active' || (mm.status as string) === 'approved';
                                                    return (
                                                    <Paper key={mm.id} elevation={0} sx={{
                                                        p: 1.25,
                                                        border: isActive ? '1px solid #a5d6a7' : '1px solid #ffe082',
                                                        borderRadius: 2,
                                                        bgcolor: isActive ? '#f1f8e9' : '#fffde7',
                                                        position: 'relative',
                                                    }}>
                                                        <Box sx={{display: 'flex', alignItems: 'center', gap: 1, pr: 4}}>
                                                            <Chip
                                                                size="small"
                                                                label={isActive ? '✅ Выбран' : '⏳ Ожидает'}
                                                                color={isActive ? 'success' : 'warning'}
                                                                sx={{height: 18, fontSize: '0.6rem', flexShrink: 0}}
                                                            />
                                                            <Typography variant="caption" fontWeight="bold" color="primary">
                                                                {mm.enstru_code}
                                                            </Typography>
                                                            {mm.matched_at && (
                                                                <Typography sx={{fontSize: '0.58rem', color: 'text.secondary', ml: 'auto', flexShrink: 0}}>
                                                                    {new Date(mm.matched_at).toLocaleString('ru-RU', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}
                                                                </Typography>
                                                            )}
                                                        </Box>
                                                        {(mm.supplier_name || mm.dvc_percent) && (
                                                            <Box sx={{mt: 0.5, pl: 0.5}}>
                                                                {mm.supplier_name && (
                                                                    <Typography sx={{fontSize: '0.62rem', color: '#334155', lineHeight: 1.3}}>
                                                                        {mm.supplier_name}
                                                                    </Typography>
                                                                )}
                                                                {mm.dvc_percent != null && (
                                                                    <Typography sx={{fontSize: '0.6rem', color: '#546e7a'}}>
                                                                        ДВС: <b>{mm.dvc_percent}%</b>
                                                                        {mm.supplier_bin && <> · БИН: {mm.supplier_bin}</>}
                                                                    </Typography>
                                                                )}
                                                            </Box>
                                                        )}
                                                        {!isReadOnlyDialog && (
                                                            <IconButton
                                                                size="small" color="error"
                                                                sx={{position: 'absolute', top: 2, right: 2}}
                                                                onClick={() => deleteMatch(mm.id)}
                                                            >
                                                                <DeleteIcon sx={{fontSize: 13}}/>
                                                            </IconButton>
                                                        )}
                                                    </Paper>
                                                    );
                                                })}
                                            </Box>
                                        ) : !editingMatch?.enstru_code && (
                                            <Typography variant="caption" color="text.secondary" sx={{p: 1, display: 'block', fontStyle: 'italic'}}>
                                                Поставщик не выбран. Найдите позицию в реестре КТП справа и нажмите «Выбрать поставщика».
                                            </Typography>
                                        )}
                                    </Box>
                                </Box>

                                <Box sx={{
                                    flex: 1,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    overflow: 'hidden',
                                    minWidth: 0
                                }}>

                                    <Box sx={{bgcolor: 'white', borderBottom: '1px solid #e0e0e0'}}>
                                        <Tabs
                                            value={searchMode}
                                            onChange={(_, v) => {
                                                setSearchMode(v as SearchMode);
                                                // Сбрасываем поиск только при ручной смене таба пользователем
                                                setReestrSearch('');
                                                setReestrResults([]);
                                            }}
                                            sx={{minHeight: 36, px: 1.5}}
                                            TabIndicatorProps={{style: {height: 2}}}
                                        >
                                            {SEARCH_TABS.map(t => (
                                                <Tab
                                                    key={t.mode}
                                                    value={t.mode}
                                                    label={
                                                        <Box sx={{display: 'flex', alignItems: 'center', gap: 0.5}}>
                                                            {t.mode === 'agsk' && <AgskIcon sx={{fontSize: 13}}/>}
                                                            {t.mode === 'name' && <CategoryIcon sx={{fontSize: 13}}/>}
                                                            {t.mode === 'all' && <SearchIcon sx={{fontSize: 13}}/>}
                                                            <span>{t.label}</span>
                                                        </Box>
                                                    }
                                                    sx={{
                                                        textTransform: 'none',
                                                        minHeight: 36,
                                                        fontSize: '0.75rem',
                                                        py: 0,
                                                        px: 1.5
                                                    }}
                                                />
                                            ))}
                                        </Tabs>

                                        <Box sx={{px: 1.5, pb: 1.5, pt: 0.5}}>
                                            <TextField
                                                fullWidth size="small"
                                                placeholder={currentSearchTab.placeholder}
                                                value={reestrSearch}
                                                onChange={e => setReestrSearch(e.target.value)}
                                                autoFocus
                                                InputProps={{
                                                    startAdornment: (
                                                        <InputAdornment position="start">
                                                            <SearchIcon fontSize="small"/>
                                                        </InputAdornment>
                                                    ),
                                                    endAdornment: reestrLoading && <CircularProgress size={16}/>,
                                                }}
                                            />
                                            {searchMode === 'agsk' && (
                                                <Typography variant="caption" color="text.secondary"
                                                            sx={{mt: 0.5, display: 'block'}}>
                                                    Введите начало кода — будут найдены все записи с совпадающим
                                                    префиксом
                                                </Typography>
                                            )}
                                        </Box>
                                    </Box>

                                    <Box sx={{
                                        flexGrow: 1,
                                        overflowY: 'auto',
                                        p: 2,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: 2
                                    }}>
                                        {reestrResults.length === 0 && debouncedReestrSearch.length >= 2 && !reestrLoading && (
                                            <Paper sx={{p: 3, textAlign: 'center', bgcolor: 'white'}}>
                                                <Typography variant="body2" color="text.secondary">Ничего не
                                                    найдено</Typography>
                                            </Paper>
                                        )}

                                        {reestrResults.length === 0 && debouncedReestrSearch.length === 0 && (
                                            <Box sx={{textAlign: 'center', mt: 4, color: '#b0bec5'}}>
                                                <SearchIcon sx={{fontSize: 40, mb: 1}}/>
                                                <Typography variant="body2">
                                                    {searchMode === 'agsk'
                                                        ? 'Введите АГСК-код или его начало (напр. 541-801)'
                                                        : 'Начните вводить для поиска в реестре КТП'}
                                                </Typography>
                                            </Box>
                                        )}

                                        {/* ── Ранее выбиралось для этого АГСК ── */}
                                        {(editingMatch?.previous_agsk_selections?.length ?? 0) > 0 && (
                                            <>
                                                <Typography sx={{
                                                    fontSize: '0.65rem', fontWeight: 'bold',
                                                    color: '#1f9a1b', textTransform: 'uppercase', letterSpacing: 0.5,
                                                }}>
                                                    🕑 Ранее выбиралось для этого АГСК
                                                </Typography>
                                        
                                                {editingMatch!.previous_agsk_selections!.map((prev, idx) => (
                                                    <Card key={`prev-${idx}`} elevation={0} sx={{
                                                        border: prev.ktp_is_active ? '1px solid #9575cd' : '1px solid #ffb74d',
                                                        borderRadius: 2,
                                                        width: '100%', boxSizing: 'border-box', flexShrink: 0,
                                                        bgcolor: prev.ktp_is_active ? '#e8f6e7' : '#fff8e1',
                                                        transition: 'all 0.2s',
                                                        ...(prev.ktp_is_active ? {'&:hover': {borderColor: '#2ca21f', boxShadow: '0 2px 8px rgba(0,0,0,0.08)'}} : {opacity: 0.8}),
                                                    }}>
                                                        <CardContent sx={{p: 2, '&:last-child': {pb: 2}}}>
                                                            <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5, gap: 1}}>
                                                                {prev.dvc_percent != null ? (
                                                                    <Chip
                                                                        label={`${prev.dvc_percent}% ДВС`} size="small"
                                                                        color={getDvcColor(prev.dvc_percent)}
                                                                        variant={prev.dvc_percent === 100 ? 'filled' : 'outlined'}
                                                                        sx={{height: 24, fontSize: '0.7rem', fontWeight: 'bold', flexShrink: 0}}
                                                                    />
                                                                ) : <Box/>}
                                                                <Box sx={{display: 'flex', gap: 0.5, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end'}}>
                                                                    <Chip
                                                                        label={`×${prev.times_selected}`} size="small"
                                                                        sx={{height: 18, fontSize: '0.6rem', bgcolor: '#e8f6e7', color: '#159c28', border: '1px solid #ce93d8', '& .MuiChip-label': {px: 0.75}}}
                                                                    />
                                                                    {!prev.ktp_is_active && (
                                                                        <Tooltip title="Поставщик стал неактивным в реестре КТП">
                                                                            <Chip label="⚠ Не активен" size="small" color="warning"
                                                                                  sx={{height: 18, fontSize: '0.6rem', '& .MuiChip-label': {px: 0.75}}}/>
                                                                        </Tooltip>
                                                                    )}
                                                                </Box>
                                                            </Box>
                                        
                                                            {prev.supplier_product && (
                                                                <Typography sx={{fontSize: '0.78rem', fontWeight: 'bold', color: '#1e293b', mb: 0.75, lineHeight: 1.3, wordBreak: 'break-word'}}>
                                                                    {prev.supplier_product}
                                                                </Typography>
                                                            )}
                                        
                                                            <Box sx={{mb: 1}}>
                                                                <Box sx={{display: 'flex', alignItems: 'flex-start', gap: 1}}>
                                                                    <BusinessIcon sx={{fontSize: 14, color: '#64748b', mt: 0.2, flexShrink: 0}}/>
                                                                    <Typography sx={{fontSize: '0.72rem', color: '#334155', wordBreak: 'break-word', lineHeight: 1.4}}>
                                                                        {prev.supplier_name || '—'}
                                                                    </Typography>
                                                                </Box>
                                                            </Box>
                                        
                                                            {prev.enstru_code && (
                                                                <Box sx={{mt: 1, pt: 1, borderTop: '1px solid #e1bee7'}}>
                                                                    <Typography sx={{fontSize: '0.65rem', color: '#546e7a', lineHeight: 1.5}}>
                                                                        <Box component="span" sx={{fontWeight: 'bold', color: '#78909c', textTransform: 'uppercase', letterSpacing: 0.3}}>ЕНСТРУ: </Box>
                                                                        <Box component="span" sx={{fontWeight: 'bold'}}>{prev.enstru_code}</Box>
                                                                    </Typography>
                                                                </Box>
                                                            )}
                                        
                                                            {/* В режиме просмотра (auto/auto_ktp) кнопка выбора скрыта */}
                                                            {isReadOnlyDialog ? null : prev.ktp_is_active && prev.ktp_id ? (
                                                                <Button size="small" variant="contained" disableElevation fullWidth
                                                                        onClick={() => saveMatch({
                                                                            ktp_id: prev.ktp_id!,
                                                                            enstru_code: prev.enstru_code,
                                                                            enstru_name: '',
                                                                            company: prev.supplier_name,
                                                                            bin: prev.supplier_bin,
                                                                            product: prev.supplier_product,
                                                                            dvc_percent: prev.dvc_percent ?? 0,
                                                                        } as ReestrResult)}
                                                                        sx={{textTransform: 'none', fontSize: '0.75rem', mt: 1.5, borderRadius: 1.5, py: 0.75, bgcolor: '#23a21f', '&:hover': {bgcolor: '#1b9a26'}}}>
                                                                    Выбрать снова
                                                                </Button>
                                                            ) : (
                                                                <Button size="small" variant="outlined" disabled fullWidth
                                                                        sx={{textTransform: 'none', fontSize: '0.75rem', mt: 1.5, borderRadius: 1.5, py: 0.75}}>
                                                                    Поставщик не активен
                                                                </Button>
                                                            )}
                                                        </CardContent>
                                                    </Card>
                                                ))}
                                        
                                                <Divider sx={{my: 0.5, borderStyle: 'dashed', borderColor: '#ce93d8'}}/>
                                            </>
                                        )}

                                        {reestrResults.map(r => (
                                            <Card key={`${r.ktp_id}-${r.enstru_code}`} elevation={0} sx={{
                                                border: '1px solid #e0e0e0', borderRadius: 2,
                                                width: '100%', boxSizing: 'border-box', flexShrink: 0,
                                                transition: 'all 0.2s',
                                                '&:hover': {
                                                    borderColor: '#1976d2',
                                                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                                                }
                                            }}>
                                                <CardContent sx={{p: 2}}>
                                                    <Box sx={{
                                                        display: 'flex',
                                                        justifyContent: 'space-between',
                                                        alignItems: 'flex-start',
                                                        mb: 1.5,
                                                        gap: 1
                                                    }}>
                                                        <Chip
                                                            label={`${r.dvc_percent}% ДВС`} size="small"
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

                                                    {r.product && (
                                                        <Typography sx={{
                                                            fontSize: '0.78rem',
                                                            fontWeight: 'bold',
                                                            color: '#1e293b',
                                                            mb: 0.75,
                                                            lineHeight: 1.3,
                                                            wordBreak: 'break-word'
                                                        }}>
                                                            <Highlight text={r.product} search={debouncedReestrSearch}/>
                                                        </Typography>
                                                    )}

                                                    <Box sx={{mb: 1}}>
                                                        <Box sx={{display: 'flex', alignItems: 'flex-start', gap: 1}}>
                                                            <BusinessIcon sx={{
                                                                fontSize: 14,
                                                                color: '#64748b',
                                                                mt: 0.2,
                                                                flexShrink: 0
                                                            }}/>
                                                            <Typography sx={{
                                                                fontSize: '0.72rem',
                                                                color: '#334155',
                                                                wordBreak: 'break-word',
                                                                lineHeight: 1.4
                                                            }}>
                                                                <Highlight text={r.company}
                                                                           search={debouncedReestrSearch}/>
                                                            </Typography>
                                                        </Box>
                                                    </Box>

                                                    {/* Коды классификаторов текстом */}
                                                    {(r.oked_codes?.length || r.kpved_codes?.length || r.tnved_codes?.length || r.enstru_code || r.agsk3_codes?.length) && (
                                                        <Box sx={{mt: 1, pt: 1, borderTop: '1px solid #f0f0f0'}}>
                                                            <ClassifierText
                                                                label="ОКЭД"
                                                                codes={r.oked_codes}
                                                                names={r.oked_names}
                                                                highlight={debouncedReestrSearch}
                                                            />
                                                            <ClassifierText
                                                                label="КПВЭД"
                                                                codes={r.kpved_codes}
                                                                names={r.kpved_names}
                                                                highlight={debouncedReestrSearch}
                                                            />
                                                            <ClassifierText
                                                                label="ТНВЭД"
                                                                codes={r.tnved_codes}
                                                                names={r.tnved_names}
                                                                highlight={debouncedReestrSearch}
                                                            />
                                                            {r.enstru_code && r.enstru_code !== '—' && (
                                                                <Typography sx={{fontSize: '0.65rem', color: '#546e7a', lineHeight: 1.5, mb: 0.25}}>
                                                                    <Box component="span" sx={{fontWeight: 'bold', color: '#78909c', textTransform: 'uppercase', letterSpacing: 0.3}}>ЕНСТРУ: </Box>
                                                                    <Box component="span" sx={{fontWeight: 'bold'}}>
                                                                        <Highlight text={r.enstru_code} search={debouncedReestrSearch}/>
                                                                    </Box>
                                                                    {r.enstru_name_rus && (
                                                                        <> — <Highlight text={r.enstru_name_rus} search={debouncedReestrSearch}/></>
                                                                    )}
                                                                    {r.enstru_detail_rus && (
                                                                        <>
                                                                            <Box component="span" sx={{fontWeight: 'bold', color: '#90a4ae', mx: 0.5}}></Box>
                                                                            <Highlight text={r.enstru_detail_rus} search={debouncedReestrSearch}/>
                                                                        </>
                                                                    )}
                                                                </Typography>
                                                            )}
                                                            <ClassifierText
                                                                label="АГСК-3"
                                                                codes={r.agsk3_codes}
                                                                names={r.agsk3_names}
                                                                highlight={(searchMode === 'agsk' || searchMode === 'all') ? debouncedReestrSearch : editingMatch?.code_sn}
                                                            />
                                                        </Box>
                                                    )}

                                                    {/* В режиме просмотра (auto/auto_ktp) — без кнопки выбора */}
                                                    {!isReadOnlyDialog && (
                                                        <Button size="small" variant="contained" disableElevation fullWidth
                                                                onClick={() => saveMatch(r)}
                                                                sx={{
                                                                    textTransform: 'none',
                                                                    fontSize: '0.75rem',
                                                                    mt: 1.5,
                                                                    borderRadius: 1.5,
                                                                    py: 0.75,
                                                                    bgcolor: '#1565c0'
                                                                }}>
                                                            Выбрать поставщика
                                                        </Button>
                                                    )}
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </Box>
                                </Box>
                            </Box>
                        )}
                    </DialogContent>

                    <DialogActions sx={{px: 2, py: 1, borderTop: '1px solid #e0e0e0'}}>
                        <Box sx={{flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1}}>
                            {isReadOnlyDialog ? (
                                <>
                                    <VisibilityIcon sx={{fontSize: 16, color: 'success.main'}}/>
                                    <Typography sx={{fontSize: '0.65rem', color: 'success.main', fontWeight: 600}}>
                                        Авто-сопоставление по АГСК — выбор поставщика не требуется
                                    </Typography>
                                </>
                            ) : (
                                <>
                                    <AutoIcon sx={{fontSize: 16, color: '#64748b'}}/>
                                    <Typography sx={{fontSize: '0.65rem', color: '#64748b'}}>
                                        Выбранные поставщики попадают в Excel-отчёт после утверждения менеджером
                                    </Typography>
                                </>
                            )}
                        </Box>
                        <Button size="small" onClick={() => setEditDialogOpen(false)} variant="contained"
                                sx={{textTransform: 'none', fontWeight: 'bold'}}>
                            Готово
                        </Button>
                    </DialogActions>
                </Dialog>
            </Box>
        </Box>
    );
};

export default PsdAnalystPage;
