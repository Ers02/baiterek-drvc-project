/**
 * Чистые API-функции для страницы аналитики ПСД.
 * Не содержат UI side effects (alert/setState) — этим занимаются обёртки в компоненте.
 */
import api from '../../services/api';
import type {ExternalDocument, User, AgskEnstruMatchItem} from '../../services/api.types';
import type {AgskMatch, ReestrResult, SearchMode} from './types';

// ── Документы ──────────────────────────────────────────────────────────────

export const fetchCurrentUser = (): Promise<User> =>
    api.get('/auth/me').then(r => r.data);

export const fetchAnalysts = (): Promise<{ id: number; full_name: string }[]> =>
    api.get('/psd-analyst/analysts').then(r => r.data);

export const fetchDocuments = (assignedToMe: boolean, isTest: boolean): Promise<ExternalDocument[]> =>
    api.get('/psd-analyst/documents', {
        params: {assigned_to_me: assignedToMe, is_test: isTest},
    }).then(r => r.data);

export const fetchDocumentItems = (
    docId: number,
    params: { only_unmatched: boolean; skip: number; limit: number; search?: string },
): Promise<{ items: AgskMatch[]; total: number; pending_match_count?: number }> =>
    api.get(`/psd-analyst/document-items/${docId}`, {params}).then(r => r.data);

export const fetchDocumentItem = (docId: number, itemId: number): Promise<Partial<AgskMatch>> =>
    api.get(`/psd-analyst/document-items/${docId}/item/${itemId}`).then(r => r.data);

// ── Действия с документом ──────────────────────────────────────────────────

export const assignAnalyst = (docId: number, analystId: number, days: number) =>
    api.post(`/psd-analyst/documents/${docId}/assign-analyst`, null, {
        params: {analyst_id: analystId, days},
    });

export const submitForApproval = (docId: number) =>
    api.post(`/psd-analyst/documents/${docId}/submit-approval`);

export const approveDocument = (docId: number) =>
    api.post(`/psd-analyst/documents/${docId}/approve`);

export const rejectDocument = (docId: number, comment: string) =>
    api.post(`/psd-analyst/documents/${docId}/reject`, {comment});

export const sendToDo = (docId: number) =>
    api.post(`/psd-analyst/documents/${docId}/send-to-do`);

export const delegateAuthority = (toUserId: number, days: number) =>
    api.post('/psd-analyst/delegate', null, {params: {to_user_id: toUserId, days}});

export const downloadResultZip = (docId: number) =>
    api.get(`/psd-analyst/documents/${docId}/download-result`, {responseType: 'blob'});

export const deleteDocument = (docId: number) =>
    api.delete(`/psd-analyst/documents/${docId}`);

export const parseDocument = (docId: number) =>
    api.post(`/psd-analyst/documents/${docId}/parse`);

export const uploadTest = (formData: FormData) =>
    api.post('/psd-analyst/upload-test', formData, {
        headers: {'Content-Type': 'multipart/form-data'},
    });

// ── Поиск и сопоставления ──────────────────────────────────────────────────

export const searchEnstruInReestr = (query: string, mode: SearchMode): Promise<ReestrResult[]> =>
    api.get('/psd-analyst/search-enstru-reestr', {
        params: {query, search_mode: mode},
    }).then(r => r.data);

export const saveSupplierMatch = (itemId: number, payload: {
    enstru_code: string;
    ktp_id: number | null;
    supplier_bin: string | null;
    supplier_name: string | null;
    supplier_product: string | null;
    dvc_percent: number | null;
}) => api.post(`/psd-analyst/document-items/${itemId}/save-match`, payload);

export const setNotInKtpRegistry = (itemId: number, value: boolean) =>
    api.post(`/psd-analyst/document-items/${itemId}/not-in-ktp-registry`, {value});

// ── Библиотека сопоставлений ───────────────────────────────────────────────

export const fetchMatchesLibrary = (params: {
    date_filter: 'all' | 'today';
    skip: number;
    limit: number;
}): Promise<{ items: AgskEnstruMatchItem[]; total: number }> =>
    api.get('/psd-analyst/matches', {params}).then(r => r.data);

// ── Экспорт ────────────────────────────────────────────────────────────────

// fetchDocumentItems URL search-param: `doc_id` для export-full-report (см. ниже)


export const approveLibraryMatch = (matchId: number) =>
    api.post(`/psd-analyst/matches/${matchId}/approve`);

export const rejectLibraryMatch = (matchId: number) =>
    api.post(`/psd-analyst/matches/${matchId}/reject`);

export const deleteLibraryMatch = (matchId: number) =>
    api.delete(`/psd-analyst/matches/${matchId}`);

// ── Экспорт и заключения ───────────────────────────────────────────────────

export const exportFullReport = (docId?: number) =>
    api.get('/psd-analyst/export-full-report', {
        params: {doc_id: docId},
        responseType: 'blob',
    });

export const downloadConclusion = (docId: number) =>
    api.get(`/psd-analyst/documents/${docId}/conclusion`, {responseType: 'blob'});

export const saveAnalystComment = (docId: number, comment: string) =>
    api.post(`/psd-analyst/documents/${docId}/analyst-comment`, {comment});
