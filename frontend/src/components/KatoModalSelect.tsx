import { useState, useEffect, useMemo } from 'react';
import {
    Modal, Box, Button, Typography, List, ListItem, ListItemText,
    IconButton, Collapse, CircularProgress, Alert, Stack, Divider,
    Tabs, Tab, TextField
} from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { getKatoChildren, getKato } from '../services/api';
import type { Kato } from '../services/api';
import { useTranslation } from '../i18n/index.tsx';
import { debounce } from 'lodash';

// ... (компонент KatoItem остается без изменений)
interface KatoItemProps {
    kato: Kato;
    level: number;
    onSelect: (kato: Kato) => void;
    selectedKato: Kato | null;
    lang: 'ru' | 'kk';
    t: (key: import('../i18n/translations').Translations) => string;
}

const KatoItem: React.FC<KatoItemProps> = ({ kato, level, onSelect, selectedKato, lang, t }) => {
    const [open, setOpen] = useState(false);
    const [children, setChildren] = useState<Kato[]>([]);
    const [loadingChildren, setLoadingChildren] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isSelected = selectedKato?.id === kato.id;

    const handleToggle = async (event: React.MouseEvent) => {
        event.stopPropagation();
        if (!open && kato.has_children) {
            setLoadingChildren(true);
            setError(null);
            try {
                const fetchedChildren = await getKatoChildren(kato.id);
                setChildren(fetchedChildren);
            } catch {
                setError(t('error_loading_children'));
            } finally {
                setLoadingChildren(false);
            }
        }
        setOpen(!open);
    };

    return (
        <>
            <ListItem
                onClick={() => onSelect(kato)}
                sx={{
                    pl: level * 2 + 2,
                    backgroundColor: isSelected ? 'primary.light' : 'inherit',
                    '&:hover': {
                        backgroundColor: isSelected ? 'primary.main' : 'action.hover',
                    },
                }}
            >
                <ListItemText primary={lang === 'ru' ? kato.name_ru : kato.name_kz} />
                {kato.has_children && (
                    <IconButton edge="end" onClick={handleToggle}>
                        {loadingChildren ? <CircularProgress size={20} /> : (open ? <ExpandLess /> : <ExpandMore />)}
                    </IconButton>
                )}
            </ListItem>
            <Collapse in={open} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                    {error && (
                        <ListItem sx={{ pl: (level + 1) * 2 + 2 }}>
                            <Alert severity="error">{error}</Alert>
                        </ListItem>
                    )}
                    {children.map((childKato) => (
                        <KatoItem
                            key={childKato.id}
                            kato={childKato}
                            level={level + 1}
                            onSelect={onSelect}
                            selectedKato={selectedKato}
                            lang={lang}
                            t={t}
                        />
                    ))}
                </List>
            </Collapse>
        </>
    );
};


interface KatoModalSelectProps {
    open: boolean;
    onClose: () => void;
    onSelect: (kato: Kato | null) => void;
    currentValue: Kato | null;
    label: string;
}

const KatoModalSelect: React.FC<KatoModalSelectProps> = ({ open, onClose, onSelect, currentValue, label }) => {
    const { t, lang } = useTranslation();
    const [tab, setTab] = useState(0); // 0 for Hierarchy, 1 for Search

    // State for Hierarchy view
    const [rootKato, setRootKato] = useState<Kato[]>([]);
    const [loadingHierarchy, setLoadingHierarchy] = useState(true);
    const [errorHierarchy, setErrorHierarchy] = useState<string | null>(null);

    // State for Search view
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Kato[]>([]);
    const [loadingSearch, setLoadingSearch] = useState(false);
    const [errorSearch, setErrorSearch] = useState<string | null>(null);

    // Common state
    const [selectedKato, setSelectedKato] = useState<Kato | null>(currentValue);

    const debouncedSearch = useMemo(
        () =>
            debounce(async (query: string) => {
                if (query.length < 2) {
                    setSearchResults([]);
                    return;
                }
                setLoadingSearch(true);
                setErrorSearch(null);
                try {
                    const results = await getKato(query);
                    setSearchResults(results);
                } catch {
                    setErrorSearch(t('search_error'));
                } finally {
                    setLoadingSearch(false);
                }
            }, 500),
        [t]
    );

    useEffect(() => {
        if (tab === 1 && searchQuery) {
            debouncedSearch(searchQuery);
        }
        return () => {
            debouncedSearch.cancel();
        };
    }, [searchQuery, tab, debouncedSearch]);


    useEffect(() => {
        const fetchRootKato = async () => {
            setLoadingHierarchy(true);
            setErrorHierarchy(null);
            try {
                const data = await getKatoChildren(0);
                setRootKato(data);
            } catch {
                setErrorHierarchy(t('error_loading_kato_regions'));
            } finally {
                setLoadingHierarchy(false);
            }
        };

        if (open) {
            if (tab === 0 && rootKato.length === 0) { // Fetch only if not already fetched
                fetchRootKato();
            }
            setSelectedKato(currentValue);
        }
    }, [open, tab, currentValue, rootKato.length, t]);

    const handleSelectKato = (kato: Kato) => {
        setSelectedKato(kato);
    };

    const handleConfirm = () => {
        onSelect(selectedKato);
        onClose();
    };

    const handleCancel = () => {
        onClose();
    };

    const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
        setTab(newValue);
    };

    return (
        <Modal open={open} onClose={handleCancel}>
            <Box sx={{
                position: 'absolute', top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                width: { xs: '90%', sm: 500, md: 600 },
                bgcolor: 'background.paper', border: '1px solid #ccc', borderRadius: 2,
                boxShadow: 24, maxHeight: '80vh', display: 'flex', flexDirection: 'column',
            }}>
                <Box sx={{ p: 4, pb: 2 }}>
                    <Typography variant="h6" component="h2" gutterBottom>{label}</Typography>
                    <Tabs value={tab} onChange={handleTabChange} centered>
                        <Tab label={t('hierarchy')} />
                        <Tab label={t('search')} />
                    </Tabs>
                </Box>
                <Divider />

                <Box sx={{ flexGrow: 1, overflowY: 'auto', p: tab === 1 ? 2 : 0 }}>
                    {tab === 0 && ( // Hierarchy View
                        <>
                            {loadingHierarchy && <CircularProgress sx={{ display: 'block', m: '20px auto' }} />}
                            {errorHierarchy && <Alert severity="error" sx={{ m: 2 }}>{errorHierarchy}</Alert>}
                            {!loadingHierarchy && !errorHierarchy && (
                                <List dense>
                                    {rootKato.map((kato) => (
                                        <KatoItem key={kato.id} kato={kato} level={0} onSelect={handleSelectKato} selectedKato={selectedKato} lang={lang} t={t} />
                                    ))}
                                </List>
                            )}
                        </>
                    )}
                    {tab === 1 && ( // Search View
                        <Stack spacing={2}>
                            <TextField
                                fullWidth
                                variant="outlined"
                                label={t('kato_search_placeholder')}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                            {loadingSearch && <CircularProgress sx={{ alignSelf: 'center' }} />}
                            {errorSearch && <Alert severity="error">{errorSearch}</Alert>}
                            {!loadingSearch && searchQuery && searchResults.length === 0 && (
                                <Typography variant="body2" color="text.secondary" textAlign="center">{t('no_results')}</Typography>
                            )}
                            <List dense>
                                {searchResults.map((kato) => {
                                    const isSelected = selectedKato?.id === kato.id;
                                    return (
                                        <ListItem
                                            key={kato.id}
                                            onClick={() => handleSelectKato(kato)}
                                            sx={{
                                                backgroundColor: isSelected ? 'primary.light' : 'inherit',
                                                '&:hover': {
                                                    backgroundColor: isSelected ? 'primary.main' : 'action.hover',
                                                },
                                            }}
                                        >
                                            <ListItemText primary={`${kato.code} - ${lang === 'ru' ? kato.name_ru : kato.name_kz}`} />
                                        </ListItem>
                                    );
                                })}
                            </List>
                        </Stack>
                    )}
                </Box>

                <Divider sx={{ mt: 'auto' }} />
                <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ p: 2 }}>
                    <Button variant="outlined" onClick={handleCancel}>{t('cancel')}</Button>
                    <Button variant="contained" onClick={handleConfirm} disabled={!selectedKato}>{t('select')}</Button>
                </Stack>
            </Box>
        </Modal>
    );
};

export default KatoModalSelect;
