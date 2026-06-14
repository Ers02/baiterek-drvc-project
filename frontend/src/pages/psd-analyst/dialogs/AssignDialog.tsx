import {useEffect, useState} from 'react';
import {
    Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControl, InputLabel, MenuItem, Select, Stack, TextField,
} from '@mui/material';

interface Props {
    open: boolean;
    onClose: () => void;
    analysts: { id: number; full_name: string; role_label?: string }[];
    onSubmit: (analystId: number, days: number) => Promise<void> | void;
    loading: boolean;
}

export default function AssignDialog({open, onClose, analysts, onSubmit, loading}: Props) {
    const [analystId, setAnalystId] = useState<number | ''>('');
    const [days, setDays] = useState(5);

    // Сбрасываем поля при каждом открытии
    useEffect(() => {
        if (open) {
            setAnalystId('');
            setDays(5);
        }
    }, [open]);

    const handleSubmit = () => {
        if (!analystId) return;
        void onSubmit(analystId as number, days);
    };

    return (
        <Dialog open={open} onClose={() => !loading && onClose()} maxWidth="xs" fullWidth>
            <DialogTitle sx={{fontWeight: 'bold'}}>Назначить аналитика</DialogTitle>
            <DialogContent>
                <Stack spacing={3} sx={{mt: 1}}>
                    <FormControl fullWidth size="small">
                        <InputLabel>Выберите аналитика</InputLabel>
                        <Select
                            value={analystId}
                            label="Выберите аналитика"
                            onChange={(e) => setAnalystId(e.target.value as number)}
                        >
                            {analysts.map(a => (
                                <MenuItem key={a.id} value={a.id}>
                                    {a.full_name}{a.role_label ? ` — ${a.role_label}` : ''}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <TextField
                        fullWidth
                        label="Срок выполнения (раб. дней)"
                        type="number"
                        size="small"
                        value={days}
                        onChange={(e) => {
                            const v = Number(e.target.value);
                            if (v > 10) setDays(10);
                            else if (v < 1) setDays(1);
                            else setDays(v);
                        }}
                        inputProps={{min: 1, max: 10}}
                        helperText={days >= 10 ? 'Максимум 10 рабочих дней' : ''}
                        error={days > 10}
                    />
                </Stack>
            </DialogContent>
            <DialogActions sx={{p: 2}}>
                <Button onClick={onClose}>Отмена</Button>
                <Button
                    variant="contained"
                    onClick={handleSubmit}
                    disabled={loading || !analystId}
                    startIcon={loading && <CircularProgress size={16} color="inherit"/>}
                >
                    Назначить
                </Button>
            </DialogActions>
        </Dialog>
    );
}
