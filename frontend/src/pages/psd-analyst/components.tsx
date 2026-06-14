import React from 'react';
import {Box, Typography, Paper, LinearProgress} from '@mui/material';
import type {DocumentStats} from './types';

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

const fmt = (n: number) =>
    new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 0}).format(n);

const TYPE_CONFIG = [
    {key: 'GOODS', label: 'Товары', color: '#1565c0'},
    {key: 'WORKS', label: 'Работы', color: '#2e7d32'},
    {key: 'SERVICES', label: 'Услуги', color: '#e65100'},
    {key: 'OTHER', label: 'Прочее', color: '#546e7a'},
];

export const DocumentDashboard: React.FC<{stats: DocumentStats | null}> = ({stats}) => {
    if (!stats) return null;

    const matchPct = stats.goods_total > 0
        ? Math.round((stats.goods_matched / stats.goods_total) * 100)
        : 0;
    const matchColor = matchPct === 100 ? '#2e7d32' : matchPct > 0 ? '#e65100' : '#9e9e9e';

    return (
        <Box sx={{display: 'flex', gap: 1.5, flexWrap: 'wrap', mb: 2}}>
            <Paper elevation={0} sx={{
                p: 1.5, flex: '1 1 150px', minWidth: 140,
                border: '1px solid #e0e0e0', borderLeft: '4px solid #1565c0', borderRadius: 2,
            }}>
                <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.2}}>
                    Итого
                </Typography>
                <Typography fontWeight="bold" sx={{fontSize: '1rem', lineHeight: 1.4}}>
                    {fmt(stats.total_amount)} ₸
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    {stats.total_items} позиций
                </Typography>
            </Paper>

            {TYPE_CONFIG.map(({key, label, color}) => {
                const t = stats.by_type[key];
                const count = t?.count ?? 0;
                const amount = t?.amount ?? 0;
                const isEmpty = count === 0;
                return (
                    <Paper key={key} elevation={0} sx={{
                        p: 1.5, flex: '1 1 120px', minWidth: 110,
                        border: '1px solid #e0e0e0',
                        borderLeft: `4px solid ${isEmpty ? '#e0e0e0' : color}`,
                        borderRadius: 2,
                        opacity: isEmpty ? 0.55 : 1,
                    }}>
                        <Typography variant="caption" sx={{
                            display: 'block', lineHeight: 1.2,
                            color: isEmpty ? '#bdbdbd' : color,
                            fontWeight: 'bold',
                        }}>
                            {label}
                        </Typography>
                        <Typography fontWeight="bold" sx={{
                            fontSize: '0.9rem', lineHeight: 1.4,
                            color: isEmpty ? '#bdbdbd' : 'text.primary',
                        }}>
                            {fmt(amount)} ₸
                        </Typography>
                        <Typography variant="caption" color={isEmpty ? '#bdbdbd' : 'text.secondary'}>
                            {count} поз.
                        </Typography>
                    </Paper>
                );
            })}

            {stats.goods_total > 0 && (
                <Paper elevation={0} sx={{
                    p: 1.5, flex: '1 1 140px', minWidth: 130,
                    border: '1px solid #e0e0e0',
                    borderLeft: `4px solid ${matchColor}`,
                    borderRadius: 2,
                }}>
                    <Typography variant="caption" color="text.secondary" sx={{display: 'block', lineHeight: 1.2}}>
                        Сопоставлено
                    </Typography>
                    <Typography fontWeight="bold" sx={{fontSize: '1rem', lineHeight: 1.4, color: matchColor}}>
                        {stats.goods_matched} / {stats.goods_total}
                    </Typography>
                    <LinearProgress
                        variant="determinate"
                        value={matchPct}
                        color={matchPct === 100 ? 'success' : 'warning'}
                        sx={{mt: 0.5, mb: 0.25, height: 4, borderRadius: 2}}
                    />
                    <Typography variant="caption" color="text.secondary">
                        {matchPct}% товаров
                    </Typography>
                </Paper>
            )}

            {(stats.by_type['GOODS']?.count ?? 0) > 0 && (() => {
                const dvc = stats.goods_dvc_percent;
                const dvcColor = dvc >= 50 ? '#2e7d32' : dvc >= 20 ? '#e65100' : '#9e9e9e';
                return (
                    <Paper elevation={0} sx={{
                        p: 1.5, flex: '1 1 140px', minWidth: 130,
                        border: '1px solid #e0e0e0',
                        borderLeft: `4px solid ${dvcColor}`,
                        borderRadius: 2,
                    }}>
                        <Typography variant="caption" sx={{display: 'block', lineHeight: 1.2, color: dvcColor, fontWeight: 'bold'}}>
                            ВЦ по товарам
                        </Typography>
                        <Typography fontWeight="bold" sx={{fontSize: '1rem', lineHeight: 1.4, color: dvcColor}}>
                            {dvc.toFixed(1)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            {fmt(stats.goods_vc_amount)} ₸
                        </Typography>
                    </Paper>
                );
            })()}
        </Box>
    );
};
