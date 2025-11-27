// src/i18n/index.ts
import { useState } from 'react'

export type Lang = 'ru' | 'kk'

const translations = {
  ru: {
    create_application: 'Создание новой заявки',
    edit_application: 'Заявка №{number}',
    draft: 'Черновик',
    submitted: 'Подана',
    enstru_search: '1. Код по ЕНС ТРУ (enstru.kz)',
    enstru_placeholder: 'Введите код или название...',
    enstru_data: 'Данные по коду ЕНС ТРУ',
    enstru_name: 'Наименование закупаемых ТРУ',
    enstru_specs: 'Характеристики (по коду ЕНС ТРУ)',
    enstru_unit: 'Единица измерения',
    fill_form: '2. Заполните заявку',
    need_type: 'Вид потребности',
    need_type_goods: 'Товар',
    need_type_works: 'Работа',
    need_type_services: 'Услуга',
    additional_specs: 'Дополнительная характеристика товаров, работ и услуг',
    agsk_3: 'АГСК-3 (для СМР)',
    expense_item: 'Статья затрат',
    funding_source: 'Источник финансирования',
    republic_budget: 'Республиканский бюджет',
    local_budget: 'Местный бюджет',
    own_funds: 'Собственные средства',
    kato_purchase: 'Код КАТО места закупки',
    kato_delivery: 'Код КАТО места поставки',
    quantity: 'Количество / объем',
    price: 'Маркетинговая цена (без НДС)',
    total: 'Сумма планируемая (без НДС)',
    is_ktp: 'Признак КТП / Резидентства РК',
    ktp_applicable: 'Применима ли закупка у КТП',
    select_first: 'Выберите код ЕНС ТРУ выше',
    will_appear: 'После этого появятся все поля для заполнения',
    cancel: 'Отмена',
    save_draft: 'Сохранить черновик',
    saving: 'Сохранение...',
    submit: 'Отправить на согласование',
    error_load: 'Не удалось загрузить заявку',
    error_save: 'Ошибка сохранения',
    error_submit: 'Ошибка отправки на согласование',
  },
  kk: {
    create_application: 'Жаңа өтініш құру',
    edit_application: '№{number} өтініш',
    draft: 'Жоба',
    submitted: 'Жіберілді',
    enstru_search: '1. ЕНС ТРУ коды (enstru.kz)',
    enstru_placeholder: 'Код немесе атауын енгізіңіз...',
    enstru_data: 'ЕНС ТРУ коды бойынша деректер',
    enstru_name: 'Сатып алынатын ТРУ атауы',
    enstru_specs: 'Сипаттамалары (ЕНС ТРУ коды бойынша)',
    enstru_unit: 'Өлшем бірлігі',
    fill_form: '2. Өтінішті толтырыңыз',
    need_type: 'Қажеттілік түрі',
    need_type_goods: 'Тауар',
    need_type_works: 'Жұмыс',
    need_type_services: 'Қызмет',
    additional_specs: 'Тауарлардың, жұмыстардың және қызметтердің қосымша сипаттамасы',
    agsk_3: 'АГСК-3 (ҚҚЖ үшін)',
    expense_item: 'Шығыс бабы',
    funding_source: 'Қаржыландыру көзі',
    republic_budget: 'Республикалық бюджет',
    local_budget: 'Жергілікті бюджет',
    own_funds: 'Өз қаражаты',
    kato_purchase: 'Сатып алу орнының КАТО коды',
    kato_delivery: 'Жеткізу орнының КАТО коды',
    quantity: 'Саны / көлемі',
    price: 'Нарықтық бағасы (ҚҚС-сыз)',
    total: 'Жоспарланған сома (ҚҚС-сыз)',
    is_ktp: 'ОТӨ белгісі / ҚР резиденттігі',
    ktp_applicable: 'ОТӨ-дан сатып алу қолданыла ма',
    select_first: 'Жоғарыдан ЕНС ТРУ кодын таңдаңыз',
    will_appear: 'Содан кейін барлық толтыру өрістері пайда болады',
    cancel: 'Бас тарту',
    save_draft: 'Жоба ретінде сақтау',
    saving: 'Сақталуда...',
    submit: 'Келісуге жіберу',
    error_load: 'Өтінішті жүктеу мүмкін болмады',
    error_save: 'Сақтау қатесі',
    error_submit: 'Жіберу қатесі',
  },
}

export const t = (key: keyof typeof translations.ru, vars?: Record<string, string | number>): string => {
  const lang: Lang = (localStorage.getItem('lang') as Lang) || (navigator.language.startsWith('kk') ? 'kk' : 'ru')
  let text: string = translations[lang][key] || translations.ru[key] || key

  if (vars) {
    Object.entries(vars).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
    })
  }

  return text
}

export const useLang = (): [Lang, (l: Lang) => void] => {
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem('lang') as Lang
    return saved || (navigator.language.startsWith('kk') ? 'kk' : 'ru')
  })

  const changeLang = (l: Lang) => {
    setLang(l)
    localStorage.setItem('lang', l)
  }

  return [lang, changeLang]
}