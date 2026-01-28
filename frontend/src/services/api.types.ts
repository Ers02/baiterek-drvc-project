// --- Типы Справочников ---
export interface Mkei { id: number; code: string; name_ru: string; name_kz: string; }
export interface Kato { id: number; parent_id: number | null; code: string; name_ru: string; name_kz: string; }
export interface Agsk { id: number; group: string; code: string; name_ru: string; }
export interface CostItem { id: number; name_ru: string; name_kz: string; }
export interface SourceFunding { id: number; name_ru: string; name_kz: string; }

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

export interface UserLookup { id: number; full_name: string; }

// --- Основные Типы ---
export type NeedType = "Товар" | "Работа" | "Услуга";
export enum PlanStatus {
  DRAFT = "DRAFT",
  PRE_APPROVED = "PRE_APPROVED",
  APPROVED = "APPROVED",
}

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
  
  // Новое поле для ВЦ
  min_dvc_percent: number;
  
  additional_specs?: string;
  additional_specs_kz?: string;
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
  agsk_id?: string;
  kato_purchase_id?: number;
  kato_delivery_id?: number;
  additional_specs?: string;
  additional_specs_kz?: string;
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
  residency_code: string;
  origin_code: string;
  contract_number: string;
  contract_date: string;
  contract_quantity: number;
  contract_price_per_unit: number;
  contract_sum: number;
  supply_volume_physical: number;
  supply_volume_value: number;
}

export interface ExecutionPayload {
  plan_item_id: number;
  supplier_name: string;
  supplier_bin: string;
  residency_code: string;
  origin_code: string;
  contract_number: string;
  contract_date: string;
  contract_quantity: number;
  contract_price_per_unit: number;
  supply_volume_physical: number;
  supply_volume_value: number;
}
