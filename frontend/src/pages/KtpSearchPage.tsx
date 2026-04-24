import { useState, useEffect } from 'react';
import {
  Box, Typography, Button, Paper, Chip, IconButton, TextField,
  Dialog, DialogTitle, DialogContent, DialogActions,
  InputAdornment, Stack, Checkbox, Tooltip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Fab, Zoom
} from '@mui/material';
import {
  Search as SearchIcon, Clear as ClearIcon, Inventory as InventoryIcon,
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
  LibraryBooks as LibraryBooksIcon, Close as CloseIcon,
  Save as SaveIcon
} from '@mui/icons-material';
import Header from '../components/Header';
import {
  getOked, getKpved, getTnved, getEnstru, getAgsk, searchKtpAdvanced,
  getProductGroups, getProductGroup, createProductGroup, updateProductGroup, deleteProductGroup
} from '../services/api';
import type {
  Oked, Kpved, Tnved, Enstru, Agsk, KtpSearchResult,
  ProductGroup, ProductGroupCreate
} from '../services/api.types';

// Тип для редактируемой группы
interface EditableGroup extends ProductGroup {
  isEditing?: boolean;
  isNew?: boolean;
  // Счетчики для отображения в режиме просмотра
  oked_count?: number;
  kpved_count?: number;
  enstru_count?: number;
  agsk3_count?: number;
  tnved_count?: number;
  reestr_ktp_count?: number;
}

// Модальный компонент для выбора справочника
interface LookupModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  searchPlaceholder: string;
  fetchData: (q?: string) => Promise<any[]>;
  selectedItems: any[];
  onSelect: (items: any[]) => void;
  getOptionLabel: (item: any) => string;
  extractCode: (item: any) => string;
}

const LookupModal: React.FC<LookupModalProps> = ({
  open, onClose, title, searchPlaceholder, fetchData, selectedItems, onSelect, getOptionLabel, extractCode
}) => {
  const [options, setOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [tempSelected, setTempSelected] = useState<any[]>([]);

  useEffect(() => {
    if (open) {
      setTempSelected(selectedItems);
      loadOptions();
    }
  }, [open, selectedItems]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadOptions(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadOptions = async (q?: string) => {
    setLoading(true);
    try {
      const data = await fetchData(q);
      // Фильтруем опции с пустыми кодами
      const validOptions = data.filter(item => {
        const code = extractCode(item);
        return code && code.trim() !== '';
      });
      setOptions(validOptions);
    } catch (err) {
      console.error('Failed to load options:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (item: any) => {
    const code = extractCode(item);
    // Игнорируем пустые коды
    if (!code || code.trim() === '') return;

    const exists = tempSelected.includes(code);
    if (exists) {
      setTempSelected(tempSelected.filter(c => c !== code));
    } else {
      setTempSelected([...tempSelected, code]);
    }
  };

  const handleSave = () => {
    onSelect(tempSelected);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: '16px' } }}>
      <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>{title}</DialogTitle>
      <DialogContent>
        <TextField
          fullWidth
          size="small"
          placeholder={searchPlaceholder}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
            endAdornment: loading ? <Box sx={{ width: 18, height: 18, border: '2px solid #ccc', borderTop: '2px solid #1a237e', borderRadius: '50%', animation: 'spin 1s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} /> : null,
          }}
          sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: '10px' } }}
        />

        {tempSelected.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              Выбрано ({tempSelected.length}):
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {tempSelected.map(code => (
                <Chip key={code} size="small" label={code} onDelete={() => handleToggle({ code })} color="primary" />
              ))}
            </Box>
          </Box>
        )}

        <Paper variant="outlined" sx={{ maxHeight: '50vh', overflow: 'auto', borderRadius: '10px' }}>
          {options.map((option) => {
            const code = extractCode(option);
            const isSelected = tempSelected.includes(code);
            // Используем id как fallback для key если код пустой
            const uniqueKey = code || option.id?.toString() || Math.random().toString();
            return (
              <Box
                key={uniqueKey}
                onClick={() => handleToggle(option)}
                sx={{
                  p: 1.5,
                  cursor: 'pointer',
                  borderBottom: '1px solid #eee',
                  bgcolor: isSelected ? '#e3f2fd' : 'white',
                  '&:hover': { bgcolor: isSelected ? '#e3f2fd' : '#f5f5f5' },
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                }}
              >
                <Checkbox checked={isSelected} size="small" />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: isSelected ? 600 : 400 }}>
                    {getOptionLabel(option)}
                  </Typography>
                </Box>
              </Box>
            );
          })}
          {options.length === 0 && !loading && (
            <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
              <Typography variant="body2">Ничего не найдено</Typography>
            </Box>
          )}
        </Paper>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button onClick={onClose} sx={{ textTransform: 'none' }}>Отмена</Button>
        <Button onClick={handleSave} variant="contained" sx={{ textTransform: 'none', fontWeight: 600 }}>
          Сохранить ({tempSelected.length})
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const KtpSearchPage: React.FC = () => {
  // Состояние
  const [groups, setGroups] = useState<EditableGroup[]>([]);
  const [loading, setLoading] = useState(false);

  // Модальное окно справочника
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'oked' | 'kpved' | 'enstru' | 'agsk3' | 'tnved' | 'reestrKtp' | null>(null);
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null);

  // Загрузка групп
  const loadGroups = async () => {
    setLoading(true);
    try {
      const data = await getProductGroups();
      setGroups(data.map(g => ({
        ...g,
        oked_codes: g.oked_codes || [],
        kpved_codes: g.kpved_codes || [],
        enstru_codes: g.enstru_codes || [],
        agsk3_codes: g.agsk3_codes || [],
        tnved_codes: g.tnved_codes || [],
        reestr_ktp_codes: g.reestr_ktp_codes || [],
        // Сохраняем счетчики для отображения в режиме просмотра
        oked_count: g.oked_count || 0,
        kpved_count: g.kpved_count || 0,
        enstru_count: g.enstru_count || 0,
        agsk3_count: g.agsk3_count || 0,
        tnved_count: g.tnved_count || 0,
        reestr_ktp_count: g.reestr_ktp_count || 0
      })));
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  // Добавить новую группу
  const addNewGroup = () => {
    const newGroup: EditableGroup = {
      id: -Date.now(),
      name: '',
      oked_codes: [],
      kpved_codes: [],
      enstru_codes: [],
      agsk3_codes: [],
      tnved_codes: [],
      reestr_ktp_codes: [],
      isEditing: true,
      isNew: true
    };
    setGroups([newGroup, ...groups]);
  };

  // Обновить группу локально
  const updateGroupLocal = (id: number, field: keyof ProductGroup, value: any) => {
    setGroups(groups.map(g => g.id === id ? { ...g, [field]: value } : g));
  };

  // Начать редактирование - загружаем полные данные группы
  const startEditGroup = async (id: number) => {
    setLoading(true);
    try {
      const fullGroup = await getProductGroup(id);
      setGroups(groups.map(g => g.id === id ? { ...fullGroup, isEditing: true } : g));
    } catch (err) {
      console.error('Failed to load group details:', err);
      alert('Ошибка при загрузке данных группы');
    } finally {
      setLoading(false);
    }
  };

  // Сохранить группу
  const saveGroup = async (group: EditableGroup) => {
    if (!group.name.trim()) {
      alert('Введите название группы');
      return;
    }

    setLoading(true);
    try {
      const payload: ProductGroupCreate = {
        name: group.name,
        oked_codes: group.oked_codes,
        kpved_codes: group.kpved_codes,
        enstru_codes: group.enstru_codes,
        agsk3_codes: group.agsk3_codes,
        tnved_codes: group.tnved_codes,
        reestr_ktp_codes: group.reestr_ktp_codes
      };

      if (group.isNew) {
        await createProductGroup(payload);
      } else {
        await updateProductGroup(group.id, payload);
      }

      await loadGroups();
    } catch (err) {
      console.error('Failed to save group:', err);
      alert('Ошибка при сохранении группы');
    } finally {
      setLoading(false);
    }
  };

  // Удалить группу
  const deleteGroup = async (id: number) => {
    if (!confirm('Удалить эту группу?')) return;

    if (id < 0) {
      setGroups(groups.filter(g => g.id !== id));
      return;
    }

    setLoading(true);
    try {
      await deleteProductGroup(id);
      await loadGroups();
    } catch (err) {
      console.error('Failed to delete group:', err);
      alert('Ошибка при удалении группы');
    } finally {
      setLoading(false);
    }
  };

  // Отменить редактирование
  const cancelNewGroup = (id: number) => {
    setGroups(groups.filter(g => g.id !== id));
  };

  // Открыть модальное окно
  const openLookupModal = (type: 'oked' | 'kpved' | 'enstru' | 'agsk3' | 'tnved' | 'reestrKtp', groupId: number) => {
    setModalType(type);
    setActiveGroupId(groupId);
    setModalOpen(true);
  };

  // Обработчик выбора
  const handleModalSelect = (codes: string[]) => {
    if (activeGroupId && modalType) {
      const fieldMap: Record<string, keyof ProductGroup> = {
        oked: 'oked_codes',
        kpved: 'kpved_codes',
        enstru: 'enstru_codes',
        agsk3: 'agsk3_codes',
        tnved: 'tnved_codes',
        reestrKtp: 'reestr_ktp_codes'
      };
      updateGroupLocal(activeGroupId, fieldMap[modalType], codes);
    }
    setModalOpen(false);
    setActiveGroupId(null);
    setModalType(null);
  };

  // Получить выбранные коды
  const getActiveCodes = (): string[] => {
    if (!activeGroupId || !modalType) return [];
    const group = groups.find(g => g.id === activeGroupId);
    if (!group) return [];

    const fieldMap: Record<string, keyof ProductGroup> = {
      oked: 'oked_codes',
      kpved: 'kpved_codes',
      enstru: 'enstru_codes',
      agsk3: 'agsk3_codes',
      tnved: 'tnved_codes',
      reestrKtp: 'reestr_ktp_codes'
    };
    return (group[fieldMap[modalType]] as string[]) || [];
  };

  // Конфигурация модального окна
  const getModalConfig = () => {
    switch (modalType) {
      case 'oked':
        return {
          title: 'Выбор ОКЭД',
          placeholder: 'Поиск по коду или названию...',
          fetch: getOked,
          getLabel: (item: Oked) => item.code ? `${item.code} - ${item.name_ru || ''}` : (item.name_ru || ''),
          extractCode: (item: Oked) => item.code || ''
        };
      case 'kpved':
        return {
          title: 'Выбор КПВЭД',
          placeholder: 'Поиск по коду или названию...',
          fetch: getKpved,
          getLabel: (item: Kpved) => item.code ? `${item.code} - ${item.name_ru || ''}` : (item.name_ru || ''),
          extractCode: (item: Kpved) => item.code || ''
        };
      case 'enstru':
        return {
          title: 'Выбор ЕНС ТРУ',
          placeholder: 'Поиск по коду или названию...',
          fetch: getEnstru,
          getLabel: (item: Enstru) => `${item.code} - ${item.name_rus || ''}`,
          extractCode: (item: Enstru) => item.code
        };
      case 'agsk3':
        return {
          title: 'Выбор АГСК3',
          placeholder: 'Поиск по коду или названию...',
          fetch: getAgsk,
          getLabel: (item: Agsk) => item.code ? `${item.code} - ${item.name_ru || ''}` : (item.name_ru || ''),
          extractCode: (item: Agsk) => item.code || ''
        };
      case 'tnved':
        return {
          title: 'Выбор ТНВЭД',
          placeholder: 'Поиск по коду или названию...',
          fetch: getTnved,
          getLabel: (item: Tnved) => {
            const parts = [item.code];
            if (item.tree_name) parts.push(item.tree_name);
            if (item.name && item.name !== item.tree_name) parts.push(item.name);
            return parts.join(' - ');
          },
          extractCode: (item: Tnved) => item.code || ''
        };
      case 'reestrKtp':
        return {
          title: 'Выбор из Реестра КТП',
          placeholder: 'Поиск по названию товара...',
          fetch: async (q?: string) => {
            const result = await searchKtpAdvanced({ query: q, skip: 0, limit: 50 });
            return result.items;
          },
          getLabel: (item: KtpSearchResult) => {
            const parts = [];
            if (item.product_code) parts.push(item.product_code);
            if (item.product_name) parts.push(item.product_name);
            if (item.company_name) parts.push(`(${item.company_name})`);
            if (item.dvc_percent) parts.push(`[${item.dvc_percent}%]`);
            return parts.join(' - ') || 'Без названия';
          },
          extractCode: (item: KtpSearchResult) => item.product_code || ''
        };
      default:
        return { title: '', placeholder: '', fetch: async () => [], getLabel: () => '', extractCode: () => '' };
    }
  };

  const config = getModalConfig();

  // Получить счетчик для типа
  const getCountForType = (group: EditableGroup, type: 'oked' | 'kpved' | 'enstru' | 'agsk3' | 'tnved' | 'reestrKtp'): number => {
    const countMap: Record<string, keyof EditableGroup> = {
      oked: 'oked_count',
      kpved: 'kpved_count',
      enstru: 'enstru_count',
      agsk3: 'agsk3_count',
      tnved: 'tnved_count',
      reestrKtp: 'reestr_ktp_count'
    };
    return (group[countMap[type]] as number) || 0;
  };

  // Рендер ячейки с кодами
  const renderCodesCell = (
  group: EditableGroup,
  codes: string[],
  color: 'success' | 'primary' | 'info' | 'warning' | 'secondary' | 'default',
  type: 'oked' | 'kpved' | 'enstru' | 'agsk3' | 'tnved' | 'reestrKtp'
) => {
  const count = getCountForType(group, type);
  const fieldMap: Record<string, keyof ProductGroup> = {
    oked: 'oked_codes',
    kpved: 'kpved_codes',
    enstru: 'enstru_codes',
    agsk3: 'agsk3_codes',
    tnved: 'tnved_codes',
    reestrKtp: 'reestr_ktp_codes',
  };

  if (group.isEditing) {
    const MAX_VISIBLE = 2; // сколько чипов показывать до обрезки
    const visible = codes.slice(0, MAX_VISIBLE);
    const hiddenCount = codes.length - MAX_VISIBLE;

    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'nowrap', overflow: 'hidden' }}>
        {/* Видимые чипы */}
        {visible.map((code) => (
          <Chip
            key={code}
            size="small"
            label={code}
            color={color}
            variant="outlined"
            onDelete={() =>
              updateGroupLocal(group.id, fieldMap[type], codes.filter((c) => c !== code))
            }
            sx={{ height: 22, fontSize: '0.7rem', flexShrink: 0, maxWidth: 90, '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' } }}
          />
        ))}

        {/* +N остальных — кликабельный чип, открывает модалку */}
        {hiddenCount > 0 && (
          <Tooltip title={codes.slice(MAX_VISIBLE).join(', ')}>
            <Chip
              size="small"
              label={`+${hiddenCount}`}
              color={color}
              onClick={() => openLookupModal(type, group.id)}
              sx={{ height: 22, fontSize: '0.7rem', flexShrink: 0, cursor: 'pointer', fontWeight: 700 }}
            />
          </Tooltip>
        )}

        {/* Кнопка + всегда последняя */}
        <Tooltip title="Добавить">
          <IconButton
            size="small"
            onClick={() => openLookupModal(type, group.id)}
            sx={{
              flexShrink: 0,
              p: 0,
              width: 22,
              height: 22,
              border: '1px solid',
              borderColor: `${color}.main`,
              borderRadius: '6px',
              color: `${color}.main`,
              ml: 'auto',
            }}
          >
            <AddIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Box>
    );
  }

  // Режим просмотра
  if (count > 0) {
    const typeNames: Record<string, string> = {
      oked: 'ОКЭД',
      kpved: 'КПВЭД',
      enstru: 'ЕНС',
      agsk3: 'АГСК',
      tnved: 'ТНВЭД',
      reestrKtp: 'КТП',
    };
    return (
      <Chip
        size="small"
        label={`${typeNames[type]}: ${count}`}
        color={color}
        variant="outlined"
        sx={{ height: 22, fontSize: '0.7rem' }}
      />
    );
  }

  return <Typography variant="caption" color="text.disabled">—</Typography>;
};

  return (
    <Box sx={{ bgcolor: '#f8f9fa', minHeight: '100vh' }}>
      <Header />

      <Box sx={{ p: 3 }}>
        {/* Заголовок */}
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ bgcolor: '#1a237e', p: 1.25, borderRadius: '12px', display: 'flex' }}>
            <LibraryBooksIcon sx={{ color: 'white', fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700} color="#1a237e">
              Библиотека групп/товаров
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Управление группами для аналитики
            </Typography>
          </Box>
        </Stack>

        {/* Таблица всех групп */}
        <Paper
          elevation={0}
          sx={{
            borderRadius: '16px',
            border: '1px solid #e0e0e0',
            bgcolor: 'white',
            overflow: 'hidden',
          }}
        >
          <TableContainer sx={{ maxHeight: 'calc(100vh - 220px)' }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#fafafa' }}>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '20%' }}>Товар (наименование)</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '14%' }}>ОКЭД</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '14%' }}>КПВЭД</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '14%' }}>ЕНС ТРУ</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '12%' }}>АГСК3</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '14%' }}>ТНВЭД</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '14%' }}>Реестр КТП</TableCell>
                  <TableCell sx={{ fontWeight: 700, fontSize: '0.8rem', color: '#666', width: '8%', textAlign: 'center' }}>Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {groups.length === 0 && !loading ? (
                  <TableRow>
                    <TableCell colSpan={8} sx={{ py: 6, textAlign: 'center' }}>
                      <InventoryIcon sx={{ fontSize: 48, opacity: 0.2, mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Нет сохранённых групп. Нажмите + чтобы добавить.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  groups.map((group) => (
                    <TableRow key={group.id} hover>
                      <TableCell sx={{ py: 1.5 }}>
                        {group.isEditing ? (
                          <TextField
                            fullWidth
                            size="small"
                            placeholder="Название группы..."
                            value={group.name}
                            onChange={(e) => updateGroupLocal(group.id, 'name', e.target.value)}
                            sx={{ '& .MuiOutlinedInput-root': { borderRadius: '8px', fontSize: '0.875rem' } }}
                          />
                        ) : (
                          <Typography variant="body2" fontWeight={600}>
                            {group.name}
                          </Typography>
                        )}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.oked_codes, 'success', 'oked')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.kpved_codes, 'primary', 'kpved')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.enstru_codes, 'info', 'enstru')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.agsk3_codes, 'warning', 'agsk3')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.tnved_codes, 'secondary', 'tnved')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5 }}>
                        {renderCodesCell(group, group.reestr_ktp_codes, 'default', 'reestrKtp')}
                      </TableCell>

                      <TableCell sx={{ py: 1.5, textAlign: 'center' }}>
                        <Stack direction="row" spacing={0.5} justifyContent="center">
                          {group.isEditing ? (
                            <>
                              <Tooltip title="Сохранить">
                                <IconButton size="small" onClick={() => saveGroup(group)} sx={{ color: 'success.main' }}>
                                  <SaveIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Отмена">
                                <IconButton size="small" onClick={() => group.isNew ? cancelNewGroup(group.id) : loadGroups()} sx={{ color: 'text.secondary' }}>
                                  <CloseIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </>
                          ) : (
                            <>
                              <Tooltip title="Редактировать">
                                <IconButton size="small" onClick={() => startEditGroup(group.id)} sx={{ color: 'primary.main' }}>
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Удалить">
                                <IconButton size="small" onClick={() => deleteGroup(group.id)} sx={{ color: 'error.main' }}>
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Box>

      <Zoom in={true}>
        <Fab
          color="primary"
          aria-label="add"
          onClick={addNewGroup}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            bgcolor: '#1a237e',
            '&:hover': { bgcolor: '#0d1642' },
          }}
        >
          <AddIcon />
        </Fab>
      </Zoom>

      <LookupModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setActiveGroupId(null); setModalType(null); }}
        title={config.title}
        searchPlaceholder={config.placeholder}
        fetchData={config.fetch}
        selectedItems={getActiveCodes()}
        onSelect={handleModalSelect}
        getOptionLabel={config.getLabel}
        extractCode={config.extractCode}
      />
    </Box>
  );
};

export default KtpSearchPage;