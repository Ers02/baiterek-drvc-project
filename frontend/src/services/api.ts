import axios from 'axios';
import type { 
    Mkei, Kato, Agsk, CostItem, SourceFunding, Enstru, UserLookup,
    NeedType, PlanItemVersion, ProcurementPlanVersion, ProcurementPlan, PlanItemPayload,
    Execution, ExecutionPayload
} from './api.types';
import { PlanStatus } from './api.types';

// Настройка экземпляра axios
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена авторизации
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Интерцептор для обработки ошибок (например, 401 Unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// --- API для Справочников ---
export const getMkei = (q?: string): Promise<Mkei[]> => api.get('/lookups/mkei', { params: { q } }).then(res => res.data);
export const getKato = (q?: string): Promise<Kato[]> => api.get('/lookups/kato', { params: { q } }).then(res => res.data);
export const getKatoChildren = (parent_id?: number): Promise<Kato[]> => api.get('/kato/', { params: { parent_id } }).then(res => res.data);
export const getKatoById = (id: number): Promise<Kato> => api.get(`/kato/${id}`).then(res => res.data);
export const getKatoParents = (id: number): Promise<Kato[]> => api.get(`/kato/${id}/parents`).then(res => res.data);
export const getAgsk = (q?: string): Promise<Agsk[]> => api.get('/lookups/agsk', { params: { q } }).then(res => res.data);
export const getCostItems = (q?: string): Promise<CostItem[]> => api.get('/lookups/cost-items', { params: { q } }).then(res => res.data);
export const getSourceFunding = (q?: string): Promise<SourceFunding[]> => api.get('/lookups/source-funding', { params: { q } }).then(res => res.data);
export const getEnstru = (q?: string): Promise<Enstru[]> => api.get('/lookups/enstru', { params: { q } }).then(res => res.data);
export const checkKtp = (enstruCode: string): Promise<{ is_ktp: boolean }> => api.get(`/lookups/check-ktp/${enstruCode}`).then(res => res.data);


// --- API для Планов (ProcurementPlan) ---
export const getPlans = (): Promise<ProcurementPlan[]> => api.get('/plans/').then(res => res.data);
export const getPlanById = (planId: number): Promise<ProcurementPlan> => api.get(`/plans/${planId}`).then(res => res.data);
export const createPlan = (data: { plan_name: string; year: number }): Promise<ProcurementPlan> => api.post('/plans/', data).then(res => res.data);
export const deletePlan = (planId: number): Promise<void> => api.delete(`/plans/${planId}`);

// --- API для Версий Плана (ProcurementPlanVersion) ---
export const createVersion = (planId: number): Promise<ProcurementPlanVersion> => api.post(`/plans/${planId}/versions`).then(res => res.data);
export const updateVersionStatus = (planId: number, status: PlanStatus): Promise<ProcurementPlanVersion> =>
  api.patch(`/plans/${planId}/versions/active/status`, { status }).then(res => res.data);
export const deleteLatestVersion = (planId: number): Promise<{ message: string }> => api.delete(`/plans/${planId}/versions/latest`).then(res => res.data);

export const exportVersionToExcel = async (planId: number, versionId: number): Promise<void> => {
  const response = await api.get(`/plans/${planId}/versions/${versionId}/export-excel`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `plan_${planId}_v${versionId}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

// --- API для Позиций Плана (PlanItem) ---
export const getItemById = (itemId: number): Promise<PlanItemVersion> => api.get(`/items/${itemId}`).then(res => res.data);
export const addItemToPlan = (planId: number, itemData: PlanItemPayload): Promise<PlanItemVersion> => api.post(`/plans/${planId}/items`, itemData).then(res => res.data);
export const updateItem = (itemId: number, itemData: Partial<PlanItemPayload>): Promise<PlanItemVersion> => api.put(`/items/${itemId}`, itemData).then(res => res.data);
export const deleteItem = (itemId: number): Promise<void> => api.delete(`/items/${itemId}`);
export const revertItem = (itemId: number): Promise<PlanItemVersion> => api.post(`/items/${itemId}/revert`).then(res => res.data);

// --- API для Исполнения (Execution) ---
export const createExecution = (data: ExecutionPayload): Promise<Execution> => api.post('/executions/', data).then(res => res.data);
export const getExecutionsByItem = (itemId: number): Promise<Execution[]> => api.get(`/executions/by-item/${itemId}`).then(res => res.data);
export const deleteExecution = (executionId: number): Promise<void> => api.delete(`/executions/${executionId}`);

// --- API для Импорта ---
export const downloadImportTemplate = async (): Promise<void> => {
    const response = await api.get('/plans/template/download', { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'import_template.xlsx');
    document.body.appendChild(link);
    link.click();
    link.remove();
};

export const importItems = (planId: number, file: File): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/plans/${planId}/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
};


export default api;
export { PlanStatus };
export type { 
    Mkei, Kato, Agsk, CostItem, SourceFunding, Enstru, UserLookup,
    NeedType, PlanItemVersion, ProcurementPlanVersion, ProcurementPlan, PlanItemPayload,
    Execution, ExecutionPayload
};
