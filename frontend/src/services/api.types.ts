// --- Типы Справочников ---
export interface Mkei { id: number; code: string; name_ru: string; name_kz: string; }
export interface Kato { id: number; parent_id: number | null; code: string; name_ru: string; name_kz: string; has_children: boolean; }
export interface Agsk { id: number; group: string; code: string; name_ru: string; }
export interface CostItem { id: number; name_ru: string; name_kz: string; }
export interface SourceFunding { id: number; name_ru: string; name_kz: string; }

// Новые справочники для поиска КТП
export interface Oked { id: number; code: string | null; name_ru: string | null; name_kz: string | null; parent_identificator: string | null; }
export interface Kpved { id: number; code: string | null; name_ru: string | null; name_kz: string | null; parent_identificator: string | null; }
export interface Tnved { id: number; code: string | null; tree_name: string | null; name: string | null; parent_id: number | null; is_last: boolean | null; }

// Результат поиска КТП
export interface KtpSearchResult {
    id: number;
    product_code: string | null;
    product_name: string | null;
    company_name: string | null;
    bin_iin: string | null;
    dvc_percent: string | null;
    oked_codes?: string[] | null;
    oked_names?: string[] | null;
    kpved_codes?: string[] | null;
    kpved_names?: string[] | null;
    tnved_codes?: string[] | null;
    enstru_codes?: string[] | null;
    enstru_names?: string[] | null;
    agsk3_codes?: string[] | null;
    agsk3_names?: string[] | null;
    production_address?: string | null;
    region_kato?: string | null;
}

// Обновленный интерфейс Enstru
export interface Enstru { 
    id: number; 
    code: string; 
    name_rus: string; 
    name_kaz: string; 
    type_name: string; // GOODS, WORKS, SERVICES
    detail_rus?: string; 
    detail_kaz?: string;
    uom?: string;
}

// --- Роли пользователей ---
export const UserRole = {
  ADMIN: "admin",
  DIRECTOR_DRVC: "director_drvc",
  ANALYST_DRVC: "analyst_drvc",
  ANALYST_MANAGER: "analyst_manager",
  USER: "user",
} as const;
export type UserRole = typeof UserRole[keyof typeof UserRole];

// --- Пользователь ---
export interface User {
  id: number;
  iin: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  delegated_to_id?: number;
  delegation_start?: string; // ISO date string
  delegation_end?: string;   // ISO date string
  is_director?: boolean;    // Флаг директора/делегирования (приходит с бэкенда)
  email?: string;
  phone?: string;
  bin?: string;
  org_name?: string;
}

export interface UserLookup { id: number; full_name: string; }

// --- Основные Типы ---
export type NeedType = "Товар" | "Работа" | "Услуга";
export const PlanStatus = {
  DRAFT: "DRAFT",
  PRE_APPROVED: "PRE_APPROVED",
  APPROVED: "APPROVED",
} as const;
export type PlanStatus = typeof PlanStatus[keyof typeof PlanStatus];

export interface PlanItemVersion {
  id: number;
  version_id: number;
  item_number: number;
  need_type: NeedType;
  trucode: string;
  quantity: number;
  price_per_unit: number;
  total_amount: number;
  is_ktp: boolean;
  
  // Новые поля для резидентства
  resident_share: number;
  non_resident_reason?: string;
  
  is_deleted: boolean;
  created_at: string;
  version: ProcurementPlanVersion; // Для контекста
  
  // Новые поля для истории
  root_item_id?: number;
  source_version_id?: number;
  source_version?: ProcurementPlanVersion;
  start_version_number: number;
  revision_number: number;
  
  // Новые поля для статуса исполнения
  executed_quantity: number;
  executed_amount: number;
  executed_vc_amount: number;
  
  // Новое поле для ВЦ
  min_dvc_percent: number;
  
  additional_specs?: string;
  vc_amount: number;

  enstru?: Enstru;
  unit?: Mkei;
  expense_item?: CostItem;
  funding_source?: SourceFunding;
  agsk?: Agsk;
  kato_purchase?: Kato;
  kato_delivery?: Kato;
}

export interface ProcurementPlanVersion {
  id: number;
  plan_id: number;
  version_number: number;
  status: PlanStatus;
  total_amount: number;
  import_percentage: number;
  
  // Новые поля для ВЦ
  vc_percentage: number;
  vc_amount: number;

  // Поля для статистики исполнения
  executed_vc_amount: number;
  executed_vc_percentage: number;

  is_active: boolean;
  is_executed: boolean;
  created_at: string;
  creator: UserLookup;
  items?: PlanItemVersion[];
}

export interface ProcurementPlan {
  id: number;
  plan_name: string;
  year: number;
  created_by: number;
  created_at: string;
  versions: ProcurementPlanVersion[];
}

export interface PlanItemPayload {
  trucode: string;
  unit_id?: number;
  expense_item_id: number;
  funding_source_id: number;
  agsk_code?: string;
  kato_purchase_id?: number;
  kato_delivery_id?: number;
  additional_specs?: string;
  quantity: number;
  price_per_unit: number;
  is_ktp: boolean;
  
  // Новые поля для резидентства
  resident_share?: number;
  non_resident_reason?: string;
  min_dvc_percent?: number;
}

// --- Типы для Исполнения (Execution) ---
export interface Execution {
  id: number;
  plan_item_id: number;
  supplier_name: string;
  supplier_bin: string;
  // residency_code и origin_code удалены
  contract_number: string;
  contract_date: string;
  contract_quantity: number;
  contract_price_per_unit: number;
  contract_sum: number;
  fact_vc_percentage: number; // Фактический процент ВЦ
  supply_volume_physical: number;
  supply_volume_value: number;
}

export interface ExecutionPayload {
  plan_item_id: number;
  supplier_name: string;
  supplier_bin: string;
  // residency_code и origin_code удалены
  contract_number: string;
  contract_date: string;
  contract_quantity: number;
  contract_price_per_unit: number;
  fact_vc_percentage: number; // Фактический процент ВЦ
  supply_volume_physical: number;
  supply_volume_value: number;
}

export interface KtpSupplier {
  id: number;
  bin_iin: string;
  company_name: string;
  dvc_percent?: number;
  product_name?: string;
  production_address?: string;
  email?: string;
  phone?: string;
  enstru_code?: string;
}

// --- Типы для PSD Анализа ---
export type ExternalDocumentStatus =
  "NEW" | "PARSED" | "ASSIGNED_TO_ANALYST" | "ANALYST_WORKING" |
  "FOR_APPROVAL" | "APPROVED" | "COMPLETED" | "REJECTED_BY_DIRECTOR" |
  "PROCESSING" | "ERROR" | "SENT";

export interface ExternalDocument {
  id: number;
  document_number?: string;
  doc_type: string;
  bank_name: string;
  sender_first_name?: string;
  sender_last_name?: string;
  sender_patronymic?: string;
  sender_email?: string;
  sender_phone?: string;
  external_id?: string;
  callback_url?: string;
  received_at: string; // ISO date string
  file_path: string;
  status: ExternalDocumentStatus;
  result_file_path?: string;
  error_message?: string;
  notes?: string;
  analyst_comment?: string; // Комментарий аналитика для заключения
  director_comment?: string; // Комментарий директора при возврате на доработку
  deadline_days?: number;     // Срок в рабочих днях
  deadline_at?: string;       // Рассчитанная дата дедлайна (ISO date string)
  completed_at?: string;      // ISO date string
  assigned_to?: number;
  assigned_at?: string;       // ISO date string
  is_test: boolean;
  assigned_user_name?: string; // Добавлено для удобства отображения на фронтенде
}

// --- Типы для новой системы ручных сопоставлений ---
export interface ManualMatchStatus {
    id: number;
    enstru_code: string;
    status: 'pending' | 'approved' | 'rejected';
    matched_at?: string;
    approved_at?: string;
}

/** Обратная совместимость — первый элемент массива current_manual_matches */
export type ManualMatchStatusLegacy = ManualMatchStatus | null;

export interface AgskEnstruMatchItem {
    id: number;
    agsk_code: string;
    enstru_code: string;
    doc_id?: number | null;
    item_id?: number | null;
    item_name?: string | null;
    matched_by: number;
    analyst_name?: string;
    matched_at?: string;
    is_approved: boolean;
    is_active: boolean;
    approved_by?: number | null;
    approved_by_name?: string | null;
    approved_at?: string | null;
    status: 'pending' | 'approved' | 'rejected';
}

// --- Payload для новых API запросов ---
export interface AssignAnalystPayload {
  analyst_id: number;
  days: number;
}

export interface RejectDocumentPayload {
  comment: string;
}

export interface DelegateAuthorityPayload {
  to_user_id: number;
  days: number;
}

// --- Типы для библиотеки групп/товаров ---
export interface ProductGroup {
  id: number;
  name: string;  // Название группы/товара
  oked_codes: string[];      // ["A.01.11.1"]
  kpved_codes: string[];     // ["01.11.11"]
  enstru_codes: string[];    // ["001.001.001"]
  agsk3_codes: string[];     // ["10001000"]
  tnved_codes: string[];     // ["0101.21.001"]
  reestr_ktp_codes: string[]; // ["PRD-001"] - product_code для связи
  created_at?: string;
  updated_at?: string;
  created_by?: number;
}

export interface ProductGroupListItem {
  id: number;
  name: string;
  created_at?: string;
  oked_count: number;
  kpved_count: number;
  enstru_count: number;
  agsk3_count: number;
  tnved_count: number;
  reestr_ktp_count: number;
}

export interface ProductGroupCreate {
  name: string;
  oked_codes: string[];
  kpved_codes: string[];
  enstru_codes: string[];
  agsk3_codes: string[];
  tnved_codes: string[];
  reestr_ktp_codes: string[];
}
