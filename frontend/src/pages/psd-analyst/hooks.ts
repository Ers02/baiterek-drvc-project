import {useEffect, useState} from 'react';

/**
 * Дебаунс значения — возвращает `value`, но обновляется только через `delay` мс после
 * последнего изменения. Используется чтобы не дёргать API на каждый ввод символа.
 */
export function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState(value);
    useEffect(() => {
        const handler = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(handler);
    }, [value, delay]);
    return debouncedValue;
}
