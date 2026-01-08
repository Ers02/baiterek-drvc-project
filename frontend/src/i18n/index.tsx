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
    close: 'Закрыть',
    confirm: 'Подтвердить',
    yes: 'Да',
    no: 'Нет',
    is_ktp:'КТП',
    // Header
    create_plan: 'Создать смету',
    my_procurement_plans: 'Мои сметы',

    // Dashboard
    dashboard_title: 'Мои сметы закупок',
    no_plans_found: 'Сметы не найдены.',
    no_plans_found_total: 'Сметы не найдены.',
    smeta_id: 'ID',
    smeta_year: 'Год',
    smeta_amount: 'Сумма',
    active_version_amount: 'Сумма активной версии',
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
    search_plans_placeholder: 'Поиск по названию или году...',
    all_plans: 'Все сметы',
    plan_header: 'Смета №{id} ({year})',
    plan_id_year: 'ID: {id}, Год: {year}',
    creator: 'Создатель',
    export_to_excel: 'Экспорт в Excel',
    edit_draft: 'Редактировать черновик',
    view_plan: 'Просмотр плана',
    delete_draft_version_tooltip: 'Удалить последнюю версию (черновик)',
    delete_plan_tooltip: 'Удалить план',
    confirm_delete_version: 'Вы уверены, что хотите удалить эту версию?',
    confirm_delete_plan: 'Вы уверены, что хотите удалить этот план?',
    create_new_plan_title: 'Создание новой сметы',
    plan_name: 'Название плана',
    plan_year: 'Год',
    create_button: 'Создать',
    plan_name_required: 'Введите название плана',

    // PlanForm
    smeta_form_title: 'Смета закупок на {year} год',
    smeta_items_title: 'Позиции сметы',
    plan_items_title: 'Позиции плана',
    add_item: 'Добавить позицию',
    item_number_short: '#',
    item_name: 'Наименование',
    item_unit: 'Ед. изм.',
    item_quantity: 'Кол-во',
    item_price: 'Цена',
    ktp_share: 'Доля КТП',
    import_share: 'Доля импорта',
    vc_mean: 'Среднее ВЦ',
    vc_median: 'Медиана ВЦ',
    vc_amount: 'Сумма ВЦ',
    pre_approve: 'Предварительно утвердить',
    approve_final: 'Окончательно утвердить',
    create_new_version: 'Создать новую версию',
    confirm_status_change_title: 'Подтверждение смены статуса',
    confirm_status_change_body: 'Вы действительно хотите изменить статус этой сметы? Это действие может ограничить редактирование.',
    no_items_in_plan: 'В смете пока нет позиций',
    edit_item: 'Редактировать',
    revert_item: 'Откатить изменения',
    delete_item: 'Удалить',
    execution_report: 'Отчет об исполнении',
    confirm_delete_item: 'Вы уверены, что хотите удалить эту позицию?',
    confirm_revert_item: 'Вы уверены, что хотите откатить изменения этой позиции к предыдущей версии?',
    executed_quantity: 'Исп. кол-во',
    executed_amount: 'Исп. сумма',
    executed: 'Исполнено',
    sum: 'Сумма',
    quantity: 'Количество',
    min_dvc_percent: 'Мин. ВЦ %',
    form_locked_warning: 'Форма заблокирована для редактирования. Создайте новую версию для внесения изменений.',

    // PlanItemForm
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
    
    // ExecutionModal
    execution_report_title: 'Отчет об исполнении',
    quantity_progress: 'Прогресс по количеству',
    amount_progress: 'Прогресс по сумме',
    plan: 'План',
    remaining: 'Остаток',
    add_new_record: 'Добавить новую запись',
    supplier_name: 'Наименование поставщика',
    supplier_bin: 'БИН/ИИН поставщика',
    residency_code: 'Код резидентства',
    origin_code: 'Код происхождения',
    contract_number: 'Номер договора',
    contract_date: 'Дата договора',
    contract_quantity: 'Кол-во по договору',
    contract_price: 'Цена за ед.',
    contract_sum: 'Сумма договора',
    supply_volume_physical: 'Объем поставки (нат.)',
    supply_volume_value: 'Объем поставки (стоим.)',
    add_record: 'Добавить запись',
    supplier: 'Поставщик',
    contract_info: 'Договор',
    no_records: 'Нет записей',
    max_price: 'Макс. цена',

    // StatusChip
    status_DRAFT: 'Черновик',
    status_PRE_APPROVED: 'На согласовании',
    status_APPROVED: 'Утвержденный',
    status_EXECUTED: 'Исполненные',
    
    // Errors & Messages
    error_title: 'Ошибка',
    error_loading_plans: 'Не удалось загрузить список смет.',
    error_creating_plan: 'Ошибка при создании сметы.',
    error_deleting_version: 'Ошибка при удалении версии.',
    error_deleting_plan: 'Ошибка при удалении плана.',
    error_creating_version: 'Ошибка при создании новой версии.',
    error_loading_plan: 'Не удалось загрузить смету.',
    error_exporting_excel: 'Ошибка при экспорте в Excel.',
    error_deleting_item: 'Ошибка при удалении позиции.',
    error_reverting_item: 'Ошибка при откате позиции.',
    error_loading_data: 'Ошибка загрузки данных.',
    error_fill_required_fields: 'Заполните все обязательные поля.',
    error_agsk_required_for_smr: 'Для СМР необходимо выбрать код АГСК-3.',
    error_saving: 'Ошибка при сохранении.',
    error_loading_executions: 'Ошибка загрузки отчетов.',
    fill_required_fields: 'Заполните обязательные поля.',
    error_quantity_exceeds_plan: 'Количество превышает плановое.',
    error_price_exceeds_plan: 'Цена превышает плановую.',
    error_amount_exceeds_plan: 'Сумма превышает плановую.',
    error_saving_execution: 'Ошибка сохранения отчета.',
    error_deleting_execution: 'Ошибка удаления отчета.',
    error_bin_length: 'БИН должен состоять из 12 цифр.',
    
    // KatoModal
    hierarchy: 'Иерархия',
    kato_search_placeholder: 'Поиск КАТО...',
    no_results: 'Ничего не найдено',
    select: 'Выбрать',
    error_loading_kato_regions: 'Ошибка загрузки регионов КАТО',
    search_error: 'Ошибка поиска',
    error_loading_children: 'Ошибка загрузки дочерних элементов',
  },
  kk: {
    // General
    open: 'Ашу',
    delete: 'Жою',
    save: 'Сақтау',
    cancel: 'Бас тарту',
    actions: 'Әрекеттер',
    close: 'Жабу',
    confirm: 'Растау',
    yes: 'Иә',
    no: 'Жоқ',
    is_ktp:'ҚТӨ',
    // Header
    create_plan: 'Сметаны құру',
    my_procurement_plans: 'Менің сметаларым',

    // Dashboard
    dashboard_title: 'Менің сатып алу сметаларым',
    no_plans_found: 'Сметалар табылмады.',
    no_plans_found_total: 'Сметалар табылмады.',
    smeta_id: 'ID',
    smeta_year: 'Жылы',
    smeta_amount: 'Сомасы',
    active_version_amount: 'Белсенді нұсқаның сомасы',
    current_status: 'Ағымдағы мәртебе',
    plan_details: 'Сметаның атауы',
    create_new_version_tooltip: 'Сметаның жаңа нұсқасын жасау',
    confirm_create_version: 'Сіз жаңа нұсқаны жасағыңыз келетініне сенімдісіз бе?',
    versions_history: 'Нұсқалар тарихы',
    version: 'Нұсқа',
    status: 'Мәртебесі',
    total_amount: 'Жалпы сомасы',
    creation_date: 'Құрылған уақыт',
    active: 'Белсенді',
    search:'Іздеу',
    search_plans_placeholder: 'Атауы немесе жылы бойынша іздеу...',
    all_plans: 'Барлық сметалар',
    plan_header: 'Смета №{id} ({year})',
    plan_id_year: 'ID: {id}, Жыл: {year}',
    creator: 'Жасаушы',
    export_to_excel: 'Excel-ге экспорттау',
    edit_draft: 'Жобаны өңдеу',
    view_plan: 'Жоспарды қарау',
    delete_draft_version_tooltip: 'Соңғы нұсқаны жою (жоба)',
    delete_plan_tooltip: 'Жоспарды жою',
    confirm_delete_version: 'Бұл нұсқаны жойғыңыз келетініне сенімдісіз бе?',
    confirm_delete_plan: 'Бұл жоспарды жойғыңыз келетініне сенімдісіз бе?',
    create_new_plan_title: 'Жаңа смета құру',
    plan_name: 'Жоспар атауы',
    plan_year: 'Жыл',
    create_button: 'Құру',
    plan_name_required: 'Жоспар атауын енгізіңіз',

    // PlanForm
    smeta_form_title: '{year} жылға арналған сатып алу сметасы',
    smeta_items_title: 'Смета позициялары',
    plan_items_title: 'Жоспар позициялары',
    add_item: 'Позиция қосу',
    item_number_short: '#',
    item_name: 'Атауы',
    item_unit: 'Өл. бір.',
    item_quantity: 'Саны',
    item_price: 'Бағасы',
    ktp_share: 'КТП үлесі',
    import_share: 'Импорт үлесі',
    vc_mean: 'Орташа ВЦ',
    vc_median: 'ВЦ медианасы',
    vc_amount: 'ВЦ сомасы',
    pre_approve: 'Алдын ала бекіту',
    approve_final: 'Түпкілікті бекіту',
    create_new_version: 'Жаңа нұсқа құру',
    confirm_status_change_title: 'Мәртебені өзгертуді растау',
    confirm_status_change_body: 'Осы сметаның мәртебесін өзгерткіңіз келе ме? Бұл әрекет өңдеуді шектеуі мүмкін.',
    no_items_in_plan: 'Сметада әзірге позициялар жоқ',
    edit_item: 'Өңдеу',
    revert_item: 'Өзгерістерді қайтару',
    delete_item: 'Жою',
    execution_report: 'Орындалу туралы есеп',
    confirm_delete_item: 'Бұл позицияны жойғыңыз келетініне сенімдісіз бе?',
    confirm_revert_item: 'Бұл позицияның өзгерістерін алдыңғы нұсқаға қайтарғыңыз келетініне сенімдісіз бе?',
    executed_quantity: 'Орын. саны',
    executed_amount: 'Орын. сомасы',
    executed: 'Орындалды',
    sum: 'Сомасы',
    quantity: 'Саны',
    min_dvc_percent: 'Мин. ВЦ %',
    form_locked_warning: 'Форма өңдеу үшін құлыпталған. Өзгерістер енгізу үшін жаңа нұсқа жасаңыз.',

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
    
    // ExecutionModal
    execution_report_title: 'Орындалу туралы есеп',
    quantity_progress: 'Саны бойынша прогресс',
    amount_progress: 'Сомасы бойынша прогресс',
    plan: 'Жоспар',
    remaining: 'Қалдық',
    add_new_record: 'Жаңа жазба қосу',
    supplier_name: 'Жеткізушінің атауы',
    supplier_bin: 'Жеткізушінің БСН/ЖСН',
    residency_code: 'Резиденттік коды',
    origin_code: 'Шығу тегі коды',
    contract_number: 'Шарт нөмірі',
    contract_date: 'Шарт күні',
    contract_quantity: 'Шарт бойынша саны',
    contract_price: 'Бірлік бағасы',
    contract_sum: 'Шарт сомасы',
    supply_volume_physical: 'Жеткізу көлемі (заттай)',
    supply_volume_value: 'Жеткізу көлемі (құндық)',
    add_record: 'Жазба қосу',
    supplier: 'Жеткізуші',
    contract_info: 'Шарт',
    no_records: 'Жазбалар жоқ',
    max_price: 'Макс. баға',
    error_bin_length: 'БСН 12 цифрдан тұруы керек.',

     // StatusChip
    status_DRAFT: 'Жоба',
    status_PRE_APPROVED: 'Келісуде',
    status_APPROVED: 'Бекітілген',
    status_EXECUTED: 'Орындалды',
    
    // Errors & Messages
    error_title: 'Қате',
    error_loading_plans: 'Сметалар тізімін жүктеу мүмкін болмады.',
    error_creating_plan: 'Сметаны құру кезінде қате пайда болды.',
    error_deleting_version: 'Нұсқаны жою кезінде қате пайда болды.',
    error_deleting_plan: 'Жоспарды жою кезінде қате пайда болды.',
    error_creating_version: 'Жаңа нұсқаны құру кезінде қате пайда болды.',
    error_loading_plan: 'Сметаны жүктеу мүмкін болмады.',
    error_exporting_excel: 'Excel-ге экспорттау кезінде қате пайда болды.',
    error_deleting_item: 'Позицияны жою кезінде қате пайда болды.',
    error_reverting_item: 'Позицияны қайтару кезінде қате пайда болды.',
    error_loading_data: 'Деректерді жүктеу қатесі.',
    error_fill_required_fields: 'Барлық міндетті өрістерді толтырыңыз.',
    error_agsk_required_for_smr: 'ҚҚЖ үшін АГСК-3 кодын таңдау қажет.',
    error_saving: 'Сақтау кезінде қате пайда болды.',
    error_loading_executions: 'Есептерді жүктеу қатесі.',
    fill_required_fields: 'Міндетті өрістерді толтырыңыз.',
    error_quantity_exceeds_plan: 'Саны жоспардан асады.',
    error_price_exceeds_plan: 'Бағасы жоспардан асады.',
    error_amount_exceeds_plan: 'Сомасы жоспардан асады.',
    error_saving_execution: 'Есепті сақтау қатесі.',
    error_deleting_execution: 'Есепті жою қатесі.',
    
    // KatoModal
    hierarchy: 'Иерархия',
    kato_search_placeholder: 'КАТО іздеу...',
    no_results: 'Ештеңе табылмады',
    select: 'Таңдау',
    error_loading_kato_regions: 'КАТО аймақтарын жүктеу қатесі',
    search_error: 'Іздеу қатесі',
    error_loading_children: 'Еншілес элементтерді жүктеу қатесі',
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
