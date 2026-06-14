import {useEffect, useState} from 'react';
import {
    Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
    TextField, Typography,
} from '@mui/material';
import {
    Science as ScienceIcon,
    UploadFile as UploadIcon,
} from '@mui/icons-material';

interface Props {
    open: boolean;
    onClose: () => void;
    onSubmit: (file: File, projectName: string) => Promise<void> | void;
    loading: boolean;
}

export default function UploadDialog({open, onClose, onSubmit, loading}: Props) {
    const [projectName, setProjectName] = useState('');
    const [file, setFile] = useState<File | null>(null);

    useEffect(() => {
        if (open) {
            setProjectName('');
            setFile(null);
        }
    }, [open]);

    const handleSubmit = () => {
        if (!file || !projectName) return;
        void onSubmit(file, projectName);
    };

    return (
        <Dialog open={open} onClose={() => !loading && onClose()} maxWidth="xs" fullWidth>
            <DialogTitle sx={{fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1}}>
                <ScienceIcon color="warning"/>
                Новый тестовый проект
            </DialogTitle>
            <DialogContent>
                <Typography variant="caption" color="text.secondary" sx={{mb: 2, display: 'block'}}>
                    Тестовый проект создается для личного анализа. Библиотека сопоставлений будет пополняться как обычно.
                </Typography>
                <TextField
                    fullWidth
                    label="Название проекта"
                    placeholder="Напр. Анализ ПСД школы..."
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    sx={{mb: 3, mt: 1}}
                    size="small"
                />

                <Button
                    component="label"
                    variant="outlined"
                    fullWidth
                    startIcon={<UploadIcon/>}
                    sx={{py: 2, borderStyle: 'dashed'}}
                >
                    {file ? file.name : 'Выбрать файл .kenml / .zip / .xlsx'}
                    <input
                        type="file"
                        hidden
                        accept=".kenml,.zip,.xlsx"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                </Button>
            </DialogContent>
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose} disabled={loading}>Отмена</Button>
                <Button
                    variant="contained"
                    color="warning"
                    onClick={handleSubmit}
                    disabled={loading || !file || !projectName}
                    startIcon={loading && <CircularProgress size={16} color="inherit"/>}
                >
                    {loading ? 'Загрузка...' : 'Создать'}
                </Button>
            </DialogActions>
        </Dialog>
    );
}
