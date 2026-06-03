import {useEffect, useState} from 'react';
import {
    Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography,
} from '@mui/material';

interface Props {
    open: boolean;
    onClose: () => void;
    analysts: { id: number; full_name: string }[];
    onSubmit: (toUserId: number, days: number) => Promise<void> | void;
    loading: boolean;
}

export default function DelegateDialog({open, onClose, analysts, onSubmit, loading}: Props) {
    const [toUserId, setToUserId] = useState<number | ''>('');
    const [days, setDays] = useState(14);

    useEffect(() => {
        if (open) {
            setToUserId('');
            setDays(14);
        }
    }, [open]);

    return (
        <Dialog open={open} onClose={() => !loading && onClose()} maxWidth="xs" fullWidth>
            <DialogTitle sx={{fontWeight: 'bold'}}>Делегировать полномочия</DialogTitle>
            <DialogContent>
                <Typography variant="caption" sx={{mb: 2, display: 'block'}}>
                    Временно передайте права директора выбранному аналитику на период отпуска.
                </Typography>
                <Stack spacing={3} sx={{mt: 1}}>
                    <FormControl fullWidth size="small">
                        <InputLabel>Кому передать права</InputLabel>
                        <Select
                            value={toUserId}
                            label="Кому передать права"
                            onChange={(e) => setToUserId(e.target.value as number)}
                        >
                            {analysts.map(a => (
                                <MenuItem key={a.id} value={a.id}>{a.full_name}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <TextField
                        fullWidth
                        label="Срок делегирования (календ. дней)"
                        type="number"
                        size="small"
                        value={days}
                        onChange={(e) => setDays(Number(e.target.value))}
                    />
                </Stack>
            </DialogContent>
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose}>Отмена</Button>
                <Button
                    variant="contained"
                    onClick={() => toUserId && void onSubmit(toUserId as number, days)}
                    disabled={loading || !toUserId}
                    startIcon={loading && <CircularProgress size={16} color="inherit"/>}
                >
                    Подтвердить
                </Button>
            </DialogActions>
        </Dialog>
    );
}
