"""
Сопоставление enstru ↔ agsk
- Два отдельных соединения: одно читает, другое пишет
- Предфильтрация по словарному индексу
- Учитывает name_rus + detail_rus + standard при сравнении
- Показывает прогресс с оценкой времени

Установка:
    pip install psycopg2-binary rapidfuzz

Запуск:
    python match.py
"""

import os, re, sys, time
import psycopg2, psycopg2.extras
from rapidfuzz import fuzz

# ─── Настройки ───────────────────────────────────────────────────────────────

PG = dict(
    host     = os.getenv("PG_HOST",     "localhost"),
    port     = int(os.getenv("PG_PORT", 5433)),
    dbname   = os.getenv("PG_DB",       "baiterek_db"),
    user     = os.getenv("PG_USER",     "postgres"),
    password = os.getenv("PG_PASSWORD", "root"),
)

MIN_SCORE  = 40
TOP_N      = 3
BATCH_SIZE = 200

# ─────────────────────────────────────────────────────────────────────────────

STOP_WORDS = {"из", "в", "на", "по", "для", "с", "и", "или", "а", "от", "до",
              "при", "за", "не", "под", "над", "марки", "тип", "типа",
              "мм", "см", "кг", "шт", "гост"}

def tokenize(text):
    if not text:
        return []
    words = re.findall(r"[а-яёa-z0-9][а-яёa-z0-9,./\-]*", text.lower())
    return [w for w in words if len(w) >= 2 and w not in STOP_WORDS]


def score_pair(e, a):
    name       = (e.get("name_rus")   or "").strip().lower()
    detail     = (e.get("detail_rus") or "").strip().lower()
    standard   = (e.get("standard")   or "").strip().lower()
    full       = (a.get("full_name")  or "").strip().lower()
    name_ru    = (a.get("name_ru")    or "").strip().lower()
    standart_a = (a.get("standart")   or "").strip().lower()

    if not name or not full:
        return 0, "пустые поля"

    reasons = []
    score   = 0

    # 1. Название — основа (до 50 баллов)
    if name in full:
        score += 50
        reasons.append(f"'{name}' входит в full_name")
    else:
        name_tokens = tokenize(name)
        full_tokens = set(tokenize(full))
        if name_tokens:
            matched = [t for t in name_tokens if t in full_tokens]
            ratio   = len(matched) / len(name_tokens)
            if ratio >= 0.8:
                score += 35
                reasons.append(f"{int(ratio*100)}% слов name в full_name")
            elif ratio >= 0.5:
                score += 15
                reasons.append(f"{int(ratio*100)}% слов name в full_name")
            else:
                fs = fuzz.token_set_ratio(name, full)
                if fs >= 60:
                    score += int(fs * 0.3)
                    reasons.append(f"fuzzy={fs}%")

    # 2. detail_rus — уточнение характеристик (до 30 баллов)
    if detail:
        detail_tokens = tokenize(detail)
        full_tokens   = set(tokenize(full))
        if detail_tokens:
            matched_d = [t for t in detail_tokens if t in full_tokens]
            ratio_d   = len(matched_d) / len(detail_tokens)
            if ratio_d >= 0.6:
                score += int(30 * ratio_d)
                reasons.append(f"detail совпал на {int(ratio_d*100)}%")
            elif ratio_d >= 0.3:
                score += int(15 * ratio_d)
                reasons.append(f"detail частично {int(ratio_d*100)}%")
            elif ratio_d > 0:
                score += 3
                reasons.append(f"detail слабо {int(ratio_d*100)}%")

    # 3. standard — ГОСТ, ASME и т.д. (до 20 баллов)
    if standard:
        std_tokens      = tokenize(standard)
        combined_a      = full + " " + standart_a
        combined_tokens = set(tokenize(combined_a))
        if std_tokens:
            matched_s = [t for t in std_tokens if t in combined_tokens]
            ratio_s   = len(matched_s) / len(std_tokens)
            if ratio_s >= 0.5:
                score += int(20 * ratio_s)
                reasons.append(f"стандарт совпал на {int(ratio_s*100)}%")
            elif ratio_s >= 0.2:
                score += int(10 * ratio_s)
                reasons.append(f"стандарт частично {int(ratio_s*100)}%")

    # 4. Бонус если краткое название agsk совпадает с name_rus (до 10 баллов)
    if name_ru and (name_ru in name or name in name_ru):
        score += 10
        reasons.append("name_ru≈name_rus")

    # 5. Штраф если первые слова совсем разные
    first_full = tokenize(full)[0] if tokenize(full) else ""
    first_name = tokenize(name)[0] if tokenize(name) else ""
    if first_full and first_name and fuzz.ratio(first_full, first_name) < 40:
        score = max(0, score - 20)
        reasons.append(f"первые слова разные ({first_name}≠{first_full})")

    return min(100, max(0, score)), " | ".join(reasons) or "нет совпадений"


def build_agsk_index(agsk_rows):
    """Словарный индекс: слово → [записи agsk]. Вместо перебора всех 220к."""
    index = {}
    for r in agsk_rows:
        tokens = tokenize(r.get("full_name") or r.get("name_ru") or "")
        seen = set()
        for t in tokens[:5]:
            if t not in seen:
                index.setdefault(t, []).append(r)
                seen.add(t)
    return index


def get_candidates(e, agsk_index):
    """Кандидаты с общими словами по name_rus + detail_rus + standard."""
    tokens = (
        tokenize(e.get("name_rus")   or "")[:3] +
        tokenize(e.get("detail_rus") or "")[:2] +
        tokenize(e.get("standard")   or "")[:2]
    )
    seen = set()
    result = []
    for t in tokens:
        for r in agsk_index.get(t, []):
            if r["code"] not in seen:
                seen.add(r["code"])
                result.append(r)
    return result


def create_result_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.enstru_agsk_matches (
            id              serial PRIMARY KEY,
            enstru_code     varchar(35),
            agsk_code       text,
            name_ru_enstru  text,
            name_ru_agsk    text,
            agsk_full_name  text,
            detail_enstru   text,
            standard_enstru text,
            score           int,
            reason          text,
            created_at      timestamp DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_matches_enstru ON public.enstru_agsk_matches (enstru_code);
        CREATE INDEX IF NOT EXISTS idx_matches_score  ON public.enstru_agsk_matches (score DESC);
    """)


def insert_batch(cur, rows):
    if not rows:
        return
    psycopg2.extras.execute_values(cur, """
        INSERT INTO public.enstru_agsk_matches
            (enstru_code, agsk_code, name_ru_enstru, name_ru_agsk,
             agsk_full_name, detail_enstru, standard_enstru, score, reason)
        VALUES %s
    """, [
        (r["enstru_code"], r["agsk_code"], r["name_ru_enstru"], r["name_ru_agsk"],
         r["agsk_full_name"], r["detail_enstru"], r["standard_enstru"], r["score"], r["reason"])
        for r in rows
    ])


def progress_bar(current, total, matched, start_time, width=40):
    pct     = current / total
    filled  = int(width * pct)
    bar     = "█" * filled + "░" * (width - filled)
    elapsed = time.time() - start_time
    eta     = (elapsed / current * (total - current)) if current > 0 else 0
    eta_str = f"{int(eta//60)}м {int(eta%60)}с" if eta > 0 else "--"
    print(f"\r  [{bar}] {current}/{total} ({int(pct*100)}%)  "
          f"совпадений: {matched}  осталось: ~{eta_str}   ", end="", flush=True)


def main():
    if not PG["dbname"]:
        print("❌  Укажите PG_DB")
        sys.exit(1)

    print("🔌  Подключаемся к PostgreSQL...")

    # Соединение 1: только чтение — named cursor требует autocommit=False
    conn_read = psycopg2.connect(**PG)
    conn_read.autocommit = False
    cur_read  = conn_read.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Соединение 2: только запись, коммиты батчами
    conn_write = psycopg2.connect(**PG)
    conn_write.autocommit = False
    cur_write  = conn_write.cursor()

    print("🗄️   Создаём таблицу enstru_agsk_matches...")
    create_result_table(cur_write)
    cur_write.execute("TRUNCATE public.enstru_agsk_matches RESTART IDENTITY")
    conn_write.commit()

    print("📥  Загружаем agsk и строим индекс...")
    cur_read.execute("""
        SELECT code, name_ru, full_name, "group", standart, unit
        FROM public.agsk ORDER BY code
    """)
    agsk_rows  = [dict(r) for r in cur_read.fetchall()]
    agsk_index = build_agsk_index(agsk_rows)
    print(f"    agsk: {len(agsk_rows)} записей | индекс: {len(agsk_index)} ключей")

    cur_read.execute("SELECT count(*) AS cnt FROM public.enstru WHERE is_active = true")
    total = cur_read.fetchone()["cnt"]
    print(f"    enstru: {total} записей\n")

    # Серверный курсор — тянет по 1000 строк, не грузит всё в память
    cur_stream = conn_read.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor,
        name="enstru_stream"
    )
    cur_stream.itersize = 1000
    cur_stream.execute("""
        SELECT code, name_rus, detail_rus, standard, uom
        FROM public.enstru
        WHERE is_active = true
        ORDER BY code
    """)

    print(f"🔍  Сопоставляем... (MIN_SCORE={MIN_SCORE}, TOP_N={TOP_N})\n")
    start_time    = time.time()
    processed     = 0
    total_matched = 0
    write_buffer  = []

    for e in cur_stream:
        e = dict(e)
        candidates = get_candidates(e, agsk_index)

        scored = []
        for a in candidates:
            sc, reason = score_pair(e, a)
            if sc >= MIN_SCORE:
                scored.append((sc, reason, a))

        scored.sort(key=lambda x: -x[0])

        for sc, reason, a in scored[:TOP_N]:
            write_buffer.append({
                "enstru_code":     e["code"],
                "agsk_code":       a["code"],
                "name_ru_enstru":  e["name_rus"],
                "name_ru_agsk":    a["name_ru"],
                "agsk_full_name":  a["full_name"],
                "detail_enstru":   e["detail_rus"],
                "standard_enstru": e["standard"],
                "score":           sc,
                "reason":          reason,
            })
            total_matched += 1

        processed += 1

        # commit только на write-соединении — read-курсор не трогает
        if len(write_buffer) >= BATCH_SIZE:
            insert_batch(cur_write, write_buffer)
            conn_write.commit()
            write_buffer.clear()

        if processed % 200 == 0 or processed == total:
            progress_bar(processed, total, total_matched, start_time)

    # Дописываем остаток
    if write_buffer:
        insert_batch(cur_write, write_buffer)
        conn_write.commit()

    cur_stream.close()
    cur_read.close()
    conn_read.close()

    elapsed = time.time() - start_time
    print(f"\n\n✅  Готово за {int(elapsed//60)}м {int(elapsed%60)}с")
    print(f"📊  Записей в enstru_agsk_matches: {total_matched}")

    cur_write.execute("""
        SELECT
            count(DISTINCT enstru_code)                             AS "ENSTRU с совпадениями",
            count(*)                                                AS "Всего строк",
            count(*) FILTER (WHERE score >= 80)                    AS "score >= 80",
            count(*) FILTER (WHERE score BETWEEN 60 AND 79)       AS "score 60-79",
            count(*) FILTER (WHERE score BETWEEN 40 AND 59)       AS "score 40-59"
        FROM public.enstru_agsk_matches
    """)
    conn_write.commit()
    row = dict(zip(
        [d[0] for d in cur_write.description],
        cur_write.fetchone()
    ))
    print("\n── Статистика ──────────────────────────────")
    for k, v in row.items():
        print(f"   {k:30} {v}")
    print("────────────────────────────────────────────")
    print("\nПросмотр:")
    print("  SELECT * FROM public.enstru_agsk_matches ORDER BY score DESC LIMIT 100;")

    cur_write.close()
    conn_write.close()


if __name__ == "__main__":
    main()