import { createContext, useState, useContext } from 'react';
import type { PropsWithChildren } from 'react';

export type Lang = 'ru' | 'kk';

const translations = {
  ru: {
    // General
    open: 'Открыть',
    delete: 'Удалить',
    save: 'Сохранить',
    cancel: 'Отмена',
    actions: 'Действия',
    
    // Header
    create_plan: 'Создать смету',
    my_procurement_plans: 'Мои сметы',

    // Dashboard
    dashboard_title: 'Мои сметы закупок',
    no_plans_found: 'Сметы не найдены.',
    smeta_id: 'ID',
    smeta_year: 'Год',
    smeta_amount: 'Сумма',
    active_version_amount: 'Сумма активной версий',
    current_status: 'Текущий статус',
    plan_details: 'Название сметы',
    create_new_version_tooltip:'Создать новую версию сметы',
    confirm_create_version: 'Вы уверены что хотите создать новую версию?',
    versions_history: 'История версий',
    version: 'Версия',
    status: 'Статус',
    total_amount: 'Общая сумма',
    creation_date: 'Дата создания',
    active: 'Активный',
    search:'Поиск',

    // SmetaForm (ранее PlanForm)
    smeta_form_title: 'Смета закупок на {year} год',
    smeta_items_title: 'Позиции сметы',
    add_item: 'Добавить позицию',
    item_number_short: '#',
    item_name: 'Наименование',
    item_unit: 'Ед. изм.',
    item_quantity: 'Кол-во',
    item_price: 'Цена',
    
    // SmetaItemForm
    item_form_edit_title: 'Редактирование позиции',
    item_form_new_title: 'Новая позиция сметы',
    enstru_label: '1. Выберите код ЕНС ТРУ',
    enstru_name_label: 'Наименование (ЕНС ТРУ)',
    enstru_specs_label: 'Характеристики (ЕНС ТРУ)',
    enstru_unit_label: 'Единица измерения (ЕНС ТРУ)',
    form_step2_title: '2. Заполните остальные поля',
    need_type: 'Вид потребности',
    need_type_goods: 'Товар',
    need_type_works: 'Работа',
    need_type_services: 'Услуга',
    additional_specs: 'Дополнительная характеристика',
    agsk_3: 'АГСК-3 (для СМР)',
    expense_item: 'Статья затрат',
    funding_source: 'Источник финансирования',
    kato_purchase: 'Место закупки (КАТО)',
    kato_delivery: 'Место поставки (КАТО)',
    is_ktp_label: 'Признак КТП',
    ktp_applicable_label: 'Применима ли закупка у КТП',
    is_resident_label: 'Резидентство РК',
    // StatusChip
    status_DRAFT: 'Черновик',
    status_PRE_APPROVED: 'Предварительно утвержденный',
    status_APPROVED: 'Утвержденный',
    all_plans: 'Все сметы',
    status_EXECUTED: 'Исполненные',
    // Errors
    error_title: 'Ошибка',
  },
  kk: {
    // General
    open: 'Ашу',
    delete: 'Жою',
    save: 'Сақтау',
    cancel: 'Бас тарту',
    main_actions: 'Әрекеттер',

    // Header
    create_plan: 'Сметаны құру',
    my_procurement_plans: 'Менің сметаларым',

    // Dashboard
    dashboard_title: 'Менің сатып алу сметаларым',
    no_plans_found: 'Сметалар табылмады.',
    smeta_id: 'ID',
    smeta_year: 'Жылы',
    smeta_amount: 'Сомасы',
    active_version_amount: 'Белсенді нұсқаның қосынды сомасы',
    current_status: 'Ағымдағы мәртебе',
    plan_details: 'Сметаның атауы',
    create_new_version_tooltip: 'Сметаның жаңа нұсқасын жасау',
    confirm_create_version: 'Сіз жаңа нұсқаны жасағыңыз келетініне сенімдісіз бе',
    versions_history: 'Нұсқалар тарихы',
    version: 'Нұсқа',
    status: 'Мәртебесі',
    total_amount: 'Жалпы сомасы',
    creation_date: 'Құрылған уақыт',
    active: 'Белсенді',
    search:'Іздеу',

    // SmetaForm
    smeta_form_title: '{year} жылға арналған сатып алу сметасы',
    smeta_items_title: 'Смета позициялары',
    add_item: 'Позиция қосу',
    item_number_short: '#',
    item_name: 'Атауы',
    item_unit: 'Өл. бір.',
    item_quantity: 'Саны',
    item_price: 'Бағасы',

    // SmetaItemForm
    item_form_edit_title: 'Позицияны редакциялау',
    item_form_new_title: 'Сметаның жаңа позициясы',
    enstru_label: '1. ЕНС ТРУ кодын таңдаңыз',
    enstru_name_label: 'Атауы (ЕНС ТРУ)',
    enstru_specs_label: 'Сипаттамалары (ЕНС ТРУ)',
    enstru_unit_label: 'Өлшем бірлігі (ЕНС ТРУ)',
    form_step2_title: '2. Қалған өрістерді толтырыңыз',
    need_type: 'Қажеттілік түрі',
    need_type_goods: 'Тауар',
    need_type_works: 'Жұмыс',
    need_type_services: 'Қызмет',
    additional_specs: 'Қосымша сипаттама',
    agsk_3: 'АГСК-3 (ҚҚЖ үшін)',
    expense_item: 'Шығыс бабы',
    funding_source: 'Қаржыландыру көзі',
    kato_purchase: 'Сатып алу орны (КАТО)',
    kato_delivery: 'Жеткізу орны (КАТО)',
    is_ktp_label: 'КТП белгісі',
    ktp_applicable_label: 'КТП-дан сатып алу қолданыла ма',
    is_resident_label: 'ҚР резиденттігі',
     // StatusChip
    status_DRAFT: 'Жобалдық',
    status_PRE_APPROVED: 'Алдын ала бекітілген',
    status_APPROVED: 'Бекітілген',
    all_plans: 'Барлық сметалар',
    status_EXECUTED: 'Орындалды',
    // Errors
    error_title: 'Қате',
  },
};

type Translations = keyof typeof translations.ru;

interface LangContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: Translations, vars?: Record<string, string | number>) => string;
}

const LangContext = createContext<LangContextType | undefined>(undefined);

export const LangProvider = ({ children }: PropsWithChildren) => {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = localStorage.getItem('lang') as Lang;
    return saved || (navigator.language.startsWith('kk') ? 'kk' : 'ru');
  });

  const setLang = (l: Lang) => {
    setLangState(l);
    localStorage.setItem('lang', l);
  };

  const t = (key: Translations, vars?: Record<string, string | number>): string => {
    let text: string = translations[lang]?.[key] || translations.ru[key] || String(key);
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
      });
    }
    return text;
  };

  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
};

export const useTranslation = () => {
  const context = useContext(LangContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LangProvider');
  }
  return context;
};