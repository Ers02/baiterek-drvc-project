import {Chip} from '@mui/material';
import {
    CheckCircle as CheckCircleIcon,
    Send as SendIcon,
    Reply as RejectIcon,
} from '@mui/icons-material';
import type {ExternalDocumentStatus} from '../../services/api.types';
import type {AgskMatch} from './types';

/**
 * Определяет статус позиции ПСД для отображения в таблице.
 * Учитывает выборы поставщиков, match_type и пометку «нет в реестре».
 */
export const getItemStatus = (m: AgskMatch): { label: string; color: 'success' | 'warning' | 'info' | 'error' } => {
    if (m.not_in_ktp_registry === true) {
        return {label: 'Нет в реестре КТП', color: 'warning'};
    }
    const hasActive = (m.current_manual_matches ?? []).some(
        mm => mm.status === 'active' || (mm.status as string) === 'approved'
    );
    const hasPending = (m.current_manual_matches ?? []).some(
        mm => mm.status === 'pending' && mm.is_active !== false
    );
    // Ручной выбор поставщика (не авто)
    if (m.match_type !== 'auto_ktp' && hasActive) return {label: '✅ Выбран поставщик', color: 'success'};
    if (hasPending) return {label: '⏳ Ожидает', color: 'warning'};
    if (m.match_type === 'manual') return {label: '✅ Выбран поставщик', color: 'success'};
    if (m.match_type === 'auto_ktp') return {label: '✅ Авто (КТП)', color: 'success'};
    if (m.match_type === 'suggested' && m.enstru_code) return {label: '💡 Подсказка', color: 'info'};
    return {label: '⚠ Не указано', color: 'error'};
};

/** Цвет чипа ДВС в зависимости от процента. */
export const getDvcColor = (percent: number): 'success' | 'warning' | 'default' => {
    if (percent === 100) return 'success';
    if (percent >= 70) return 'warning';
    return 'default';
};

/** Чип статуса документа ПСД (NEW / PARSED / ASSIGNED_TO_ANALYST / FOR_APPROVAL / APPROVED / …). */
export const getStatusChip = (status: ExternalDocumentStatus) => {
    switch (status) {
        case "NEW":
            return <Chip label="Новый" size="small" variant="outlined"/>;
        case "PARSED":
            return <Chip label="Распарсен" size="small" color="info" variant="outlined"/>;
        case "ASSIGNED_TO_ANALYST":
            return <Chip label="Назначен" size="small" color="primary" variant="outlined"/>;
        case "FOR_APPROVAL":
            return <Chip label="На утверждении" size="small" color="warning"/>;
        case "APPROVED":
            return <Chip label="Утвержден" size="small" color="success"/>;
        case "COMPLETED":
            return <Chip label="Завершен" size="small" color="success" variant="filled" icon={<CheckCircleIcon/>}/>;
        case "SENT":
            return <Chip label="Отправлен в ДО" size="small" color="info" variant="filled" icon={<SendIcon/>}/>;
        case "REJECTED_BY_DIRECTOR":
            return <Chip label="На доработке" size="small" color="error" variant="outlined" icon={<RejectIcon/>}/>;
        case "ERROR":
            return <Chip label="Ошибка" size="small" color="error"/>;
        default:
            return <Chip label={status} size="small" variant="outlined"/>;
    }
};
