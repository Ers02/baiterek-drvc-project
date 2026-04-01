import pandas as pd
from sqlalchemy import create_engine, text

# 1. Подключение
DB_URL = 'postgresql://postgres:root@localhost:5433/baiterek_db'
engine = create_engine(DB_URL)


def migrate_agsk():
    # Читаем данные. Нам нужны только те поля, которые участвуют в логике
    print("Загрузка данных из agsk...")
    query = 'SELECT "group", code, name_ru, standart, unit FROM agsk'
    df = pd.read_sql(query, con=engine)

    if df.empty:
        print("Таблица agsk пуста.")
        return

    # 2. Логика префиксов
    # Берем код без последних двух цифр (например, из '222-507-0101' делаем '222-507-01')
    df['prefix'] = df['code'].str[:-2]

    # Создаем мапу родителей (где код заканчивается на 00)
    is_parent = df['code'].str.endswith('00')
    # prefix -> name_ru
    parents_map = df[is_parent].set_index('prefix')['name_ru'].to_dict()

    print(f"Найдено потенциальных родителей: {len(parents_map)}")

    # 3. Трансформация
    def transform(row):
        code = row['code']
        prefix = row['prefix']
        name = row['name_ru']

        # Если это сам родитель
        if code.endswith('00'):
            return name, None

        # Ищем имя родителя по префиксу
        parent_name = parents_map.get(prefix)

        if parent_name:
            # Склеиваем: Имя родителя | Имя текущей позиции
            full_name = f"{parent_name} {name}"
            parent_code = prefix + '00'
            return full_name, parent_code
        else:
            # Если родителя '...00' не существует в базе
            return f"[СИРОТА] {name}", None

    print("Обработка иерархии (170к строк)...")
    # Применяем функцию и разбиваем результат на две колонки
    df[['full_name_ru', 'parent_code']] = df.apply(
        lambda r: pd.Series(transform(r)), axis=1
    )

    # Оставляем только нужные колонки для новой таблицы
    # Добавляем group и standart, чтобы данные не терялись
    df_agsk2 = df[['group', 'code', 'full_name_ru', 'standart', 'unit', 'parent_code']]

    # 4. Запись в новую таблицу
    print("Запись в agsk2...")
    try:
        # if_exists='replace' создаст таблицу автоматически
        df_agsk2.to_sql(
            'agsk2',
            con=engine,
            if_exists='replace',
            index=False,
            chunksize=10000,
            method='multi'
        )
        print("Миграция завершена успешно!")

        # Быстрая проверка сирот
        orphans = df_agsk2[df_agsk2['full_name_ru'].str.contains('\[СИРОТА\]')]
        if not orphans.empty:
            print(f"⚠️ Найдено сирот: {len(orphans)}")
            # Можно сохранить сирот в файл для анализа, если нужно:
            # orphans.to_csv('orphans_report.csv', index=False)

    except Exception as e:
        print(f"Ошибка при сохранении: {e}")


if __name__ == "__main__":
    migrate_agsk()