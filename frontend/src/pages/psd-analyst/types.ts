import type {ManualMatchStatus} from '../../services/api.types';

export type SearchMode = 'all' | 'agsk' | 'name';

export interface PreviousAgskSelection {
    ktp_id: number | null;
    enstru_code: string;
    supplier_bin: string;
    supplier_name: string;
    supplier_product: string;
    dvc_percent: number | null;
    times_selected: number;
    last_selected_at: string | null;
    ktp_is_active: boolean;  // false = поставщик стал неактивным в реестре КТП
}

export interface AgskMatch {
    id?: number;
    document_id?: number;
    item_id: number;
    position_number: string;
    name: string;
    code_sn: string;
    unit: string;
    volume: number;
    enstru_code?: string;
    enstru_name?: string;
    match_type: 'auto_ktp' | 'manual' | 'manual_ktp' | 'none' | 'suggested';
    match_score?: number;
    match_reason?: string;
    not_in_ktp_registry?: boolean;
    item_type?: string;
    price?: number;
    total_amount?: number;
    current_manual_matches?: ManualMatchStatus[];
    previous_agsk_selections?: PreviousAgskSelection[];
}

export interface ReestrResult {
    ktp_id: number;
    enstru_code: string;
    enstru_name: string;
    enstru_name_rus?: string;
    enstru_detail_rus?: string;
    enstru_standard?: string;
    company: string;
    bin: string;
    product: string;
    dvc_percent: number;
    localization: string;
    address: string;
    registry_date: string;
    region: string;
    agsk3_codes?: string[];
    agsk3_names?: string[];
    oked_codes?: string[];
    oked_names?: string[];
    kpved_codes?: string[];
    kpved_names?: string[];
    tnved_codes?: string[];
    tnved_names?: string[];
}

export interface DocumentStats {
    total_items: number;
    total_amount: number;
    by_type: Record<string, { count: number; amount: number }>;
    goods_total: number;
    goods_matched: number;
    goods_dvc_percent: number;
    goods_vc_amount: number;
}

export const SEARCH_TABS: { mode: SearchMode; label: string; placeholder: string }[] = [
    {mode: 'all', label: 'Все', placeholder: 'Поиск по всем полям...'},
    {mode: 'agsk', label: 'АГСК-код', placeholder: 'Напр. 541-801 или 541-801-2066-58...'},
    {mode: 'name', label: 'Название', placeholder: 'Название товара или компании...'},
];
