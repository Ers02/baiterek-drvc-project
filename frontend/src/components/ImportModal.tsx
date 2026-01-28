import React, { useState } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    Typography, Box, Alert, CircularProgress, Accordion, AccordionSummary, AccordionDetails
} from '@mui/material';
import { CloudUpload as UploadIcon, Download as DownloadIcon, ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
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

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setFile(event.target.files[0]);
            setError(null);
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

        try {
            const response = await importItems(planId, file);
            
            if (response instanceof Blob && response.type.includes('sheet')) {
                const url = window.URL.createObjectURL(response);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'import_errors.xlsx');
                document.body.appendChild(link);
                link.click();
                link.remove();
                setError(t('import_validation_error_file'));
            } else {
                onSuccess();
                onClose();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || t('error_importing_file'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>{t('import_items_title')}</DialogTitle>
            <DialogContent>
                
                <Accordion sx={{ my: 2 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography>{t('import_instructions')}</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Box sx={{
                            '& p': { my: 1 },
                            '& ol': { pl: 3 },
                            '& ul': { pl: 3 },
                            '& li': { mb: 1 },
                            '& b': { fontWeight: 'bold' }
                        }}>
                            <Typography component="div" dangerouslySetInnerHTML={{ __html: t('import_instructions_text') }} />
                        </Box>
                    </AccordionDetails>
                </Accordion>

                <Box sx={{ mb: 3, textAlign: 'center' }}>
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
