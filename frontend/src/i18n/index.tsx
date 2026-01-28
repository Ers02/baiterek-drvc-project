import { createContext, useState, useContext } from 'react';
import type { PropsWithChildren } from 'react';
import { translations } from './translations'; // Импортируем translations из нового файла

export type Lang = 'ru' | 'kk';

export type Translations = keyof typeof translations.ru; // Определяем тип здесь

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
