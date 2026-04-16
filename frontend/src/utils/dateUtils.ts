import { isWeekend, parseISO } from 'date-fns';

const KZ_HOLIDAYS_FIXED: { month: number; day: number; name: string }[] = [
  { month: 1, day: 1, name: 'Новый год' },
  { month: 1, day: 2, name: 'Новый год' },
  { month: 1, day: 7, name: 'Рождество Христово' },
  { month: 3, day: 8, name: 'Международный женский день' },
  { month: 3, day: 21, name: 'Наурыз мейрамы' },
  { month: 3, day: 22, name: 'Наурыз мейрамы' },
  { month: 3, day: 23, name: 'Наурыз мейрамы' },
  { month: 5, day: 1, name: 'Праздник единства народа Казахстана' },
  { month: 5, day: 7, name: 'День защитника Отечества' },
  { month: 5, day: 9, name: 'День Победы' },
  { month: 7, day: 6, name: 'День Столицы' },
  { month: 8, day: 30, name: 'День Конституции' },
  { month: 10, day: 25, name: 'День Республики' },
  { month: 12, day: 16, name: 'День Независимости' },
];

export function getKzHolidaysForYear(year: number): Date[] {
  return KZ_HOLIDAYS_FIXED.map(h => new Date(year, h.month - 1, h.day));
}

/**
 * Считает количество рабочих дней, ПРОШЕДШИХ с момента startDate до endDate.
 * Не учитывает сам день startDate (день поступления).
 */
export function calculateWorkingDays(startDate: string | Date, endDate: string | Date): number {
  let start = typeof startDate === 'string' ? parseISO(startDate) : new Date(startDate);
  let end = typeof endDate === 'string' ? parseISO(endDate) : new Date(endDate);

  start.setHours(0, 0, 0, 0);
  end.setHours(0, 0, 0, 0);

  if (start >= end) return 0;

  let workingDays = 0;
  // Начинаем считать со СЛЕДУЮЩЕГО дня после поступления
  let currentDate = new Date(start);
  currentDate.setDate(currentDate.getDate() + 1);

  const holidaysCache: { [year: number]: Date[] } = {};

  while (currentDate <= end) {
    const year = currentDate.getFullYear();
    if (!(year in holidaysCache)) {
      holidaysCache[year] = getKzHolidaysForYear(year);
    }

    const isCurrentDateWeekend = isWeekend(currentDate);
    const isCurrentDateHoliday = holidaysCache[year].some(holiday =>
      holiday.getMonth() === currentDate.getMonth() &&
      holiday.getDate() === currentDate.getDate()
    );

    if (!isCurrentDateWeekend && !isCurrentDateHoliday) {
      workingDays++;
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  return workingDays;
}
