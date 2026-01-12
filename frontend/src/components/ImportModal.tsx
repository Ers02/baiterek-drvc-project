import React, { useState } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    Typography, Box, Alert, CircularProgress, List, ListItem, ListItemText
} from '@mui/material';
import { CloudUpload as UploadIcon, Download as DownloadIcon } from '@mui/icons-material';
import { useTranslation } from '../i18n/index.tsx';
import { downloadImportTemplate, importItems } from '../services/api';

interface ImportModalProps {
    open: boolean;
    onClose: () => void;
    planId: number;
    onSuccess: () => void;
}

const ImportModal: React.FC<ImportModalProps> = ({ open, onClose, planId, onSuccess }) => {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [validationErrors, setValidationErrors] = useState<string[]>([]);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setFile(event.target.files[0]);
            setError(null);
            setValidationErrors([]);
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            await downloadImportTemplate();
        } catch (err) {
            setError(t('error_downloading_template'));
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);
        setValidationErrors([]);

        try {
            await importItems(planId, file);
            onSuccess();
            onClose();
        } catch (err: any) {
            if (err.response?.data?.detail?.errors) {
                setValidationErrors(err.response.data.detail.errors);
                setError(t('import_validation_error'));
            } else {
                setError(err.response?.data?.detail || t('error_importing_file'));
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>{t('import_items_title')}</DialogTitle>
            <DialogContent>
                <Box sx={{ mb: 3, textAlign: 'center' }}>
                    <Typography variant="body2" gutterBottom>
                        {t('import_instructions')}
                    </Typography>
                    <Button 
                        variant="outlined" 
                        startIcon={<DownloadIcon />} 
                        onClick={handleDownloadTemplate}
                        sx={{ mt: 1 }}
                    >
                        {t('download_template')}
                    </Button>
                </Box>

                <Box sx={{ mb: 2, p: 2, border: '1px dashed #ccc', borderRadius: 1, textAlign: 'center' }}>
                    <input
                        accept=".xlsx"
                        style={{ display: 'none' }}
                        id="raised-button-file"
                        type="file"
                        onChange={handleFileChange}
                    />
                    <label htmlFor="raised-button-file">
                        <Button variant="contained" component="span" startIcon={<UploadIcon />}>
                            {t('select_file')}
                        </Button>
                    </label>
                    {file && (
                        <Typography variant="body2" sx={{ mt: 1 }}>
                            {t('selected_file')}: {file.name}
                        </Typography>
                    )}
                </Box>

                {loading && <CircularProgress sx={{ display: 'block', mx: 'auto', mb: 2 }} />}
                
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                
                {validationErrors.length > 0 && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        <Typography variant="subtitle2">{t('validation_errors')}:</Typography>
                        <List dense sx={{ maxHeight: 150, overflow: 'auto' }}>
                            {validationErrors.map((err, index) => (
                                <ListItem key={index}>
                                    <ListItemText primary={err} />
                                </ListItem>
                            ))}
                        </List>
                    </Alert>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>{t('cancel')}</Button>
                <Button 
                    onClick={handleUpload} 
                    variant="contained" 
                    disabled={!file || loading}
                >
                    {t('upload')}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ImportModal;
