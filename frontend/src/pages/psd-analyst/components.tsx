import React from 'react';
import {Box, Typography} from '@mui/material';

/** Подсвечивает совпадение `search` в `text` жёлтым (case-insensitive). */
export const Highlight: React.FC<{ text: string; search: string }> = ({text, search}) => {
    if (!search.trim() || !text) return <>{text}</>;
    const parts = text.split(new RegExp(`(${search.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi'));
    return (
        <>
            {parts.map((part, i) =>
                part.toLowerCase() === search.toLowerCase() ? (
                    <Box component="span" key={i}
                         sx={{bgcolor: '#fff59d', color: '#000', borderRadius: '2px', px: '2px'}}>
                        {part}
                    </Box>
                ) : (
                    part
                )
            )}
        </>
    );
};

/** Строка вида «КЛАСС: code1 — name1 | code2 — name2 …» (ОКЭД / КПВЭД / ТНВЭД / АГСК-3). */
export const ClassifierText: React.FC<{
    label: string;
    codes?: string[];
    names?: string[];
    highlight?: string;
}> = ({label, codes = [], names = [], highlight = ''}) => {
    if (!codes.length) return null;
    return (
        <Typography sx={{fontSize: '0.65rem', color: '#546e7a', lineHeight: 1.5, mb: 0.25}}>
            <Box component="span" sx={{
                fontWeight: 'bold', color: '#78909c',
                textTransform: 'uppercase', letterSpacing: 0.3,
            }}>
                {label}:{' '}
            </Box>
            {codes.map((code, i) => {
                const name = names[i] || '';
                return (
                    <Box component="span" key={`${code}-${i}`}>
                        <Box component="span" sx={{fontWeight: 'bold'}}>
                            <Highlight text={code} search={highlight}/>
                        </Box>
                        {name && <> — <Highlight text={name} search={highlight}/></>}
                        {i < codes.length - 1 && (
                            <Box component="span" sx={{fontWeight: 'bold', color: '#90a4ae', mx: 0.5}}>|</Box>
                        )}
                    </Box>
                );
            })}
        </Typography>
    );
};
