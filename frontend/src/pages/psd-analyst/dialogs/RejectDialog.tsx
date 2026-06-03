import {useEffect, useState} from 'react';
import {
    Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
    TextField, Typography,
} from '@mui/material';

interface Props {
    open: boolean;
    onClose: () => void;
    onSubmit: (comment: string) => Promise<void> | void;
    loading: boolean;
}

export default function RejectDialog({open, onClose, onSubmit, loading}: Props) {
    const [comment, setComment] = useState('');

    useEffect(() => {
        if (open) setComment('');
    }, [open]);

    return (
        <Dialog open={open} onClose={() => !loading && onClose()} maxWidth="sm" fullWidth>
            <DialogTitle sx={{fontWeight: 'bold', color: 'error.main'}}>Вернуть на доработку</DialogTitle>
            <DialogContent>
                <Typography variant="body2" sx={{mb: 2}}>
                    Укажите причину возврата или необходимые исправления. Аналитик увидит этот комментарий.
                </Typography>
                <TextField
                    fullWidth
                    multiline
                    rows={4}
                    label="Комментарий аналитику"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Напр. Необходимо уточнить сопоставление по позициям..."
                />
            </DialogContent>
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose}>Отмена</Button>
                <Button
                    variant="contained"
                    color="error"
                    onClick={() => void onSubmit(comment)}
                    disabled={loading || !comment}
                    startIcon={loading && <CircularProgress size={16} color="inherit"/>}
                >
                    Вернуть аналитику
                </Button>
            </DialogActions>
        </Dialog>
    );
}
