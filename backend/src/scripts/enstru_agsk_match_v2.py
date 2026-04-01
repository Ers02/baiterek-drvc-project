"""
Эксклюзивное сопоставление agsk ↔ enstru
- Каждый enstru назначается только ОДНОМУ agsk (занят и больше не используется)
- Для каждого agsk подбирается лучший свободный enstru
- Если подходящего свободного enstru нет — agsk остаётся без пары

Алгоритм:
  1. Считаем score для всех пар agsk+enstru (через индекс, быстро)
  2. Сортируем все пары по score DESC
  3. Жадно назначаем сверху вниз: берём пару, если enstru ещё свободен — назначаем

Установка:
    pip install psycopg2-binary rapidfuzz

Запуск:
    python match_exclusive.py
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


def score_pair(a, e):
    full       = (a.get("full_name")  or "").strip().lower()
    name_ru    = (a.get("name_ru")    or "").strip().lower()
    standart_a = (a.get("standart")   or "").strip().lower()
    name       = (e.get("name_rus")   or "").strip().lower()
    detail     = (e.get("detail_rus") or "").strip().lower()
    standard   = (e.get("standard")   or "").strip().lower()

    if not name or not full:
        return 0, "пустые поля"

    reasons = []
    score   = 0

    # 1. Название enstru входит в full_name agsk (до 50 баллов)
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

    # 2. detail_rus (до 30 баллов)
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

    # 3. Стандарт (до 20 баллов)
    if standard:
        std_tokens      = tokenize(standard)
        combined_tokens = set(tokenize(full + " " + standart_a))
        if std_tokens:
            matched_s = [t for t in std_tokens if t in combined_tokens]
            ratio_s   = len(matched_s) / len(std_tokens)
            if ratio_s >= 0.5:
                score += int(20 * ratio_s)
                reasons.append(f"стандарт совпал на {int(ratio_s*100)}%")
            elif ratio_s >= 0.2:
                score += int(10 * ratio_s)
                reasons.append(f"стандарт частично {int(ratio_s*100)}%")

    # 4. Бонус краткое название (до 10 баллов)
    if name_ru and (name_ru in name or name in name_ru):
        score += 10
        reasons.append("name_ru≈name_rus")

    # 5. Штраф если первые слова разные
    first_full = tokenize(full)[0] if tokenize(full) else ""
    first_name = tokenize(name)[0] if tokenize(name) else ""
    if first_full and first_name and fuzz.ratio(first_full, first_name) < 40:
        score = max(0, score - 20)
        reasons.append(f"первые слова разные ({first_name}≠{first_full})")

    return min(100, max(0, score)), " | ".join(reasons) or "нет совпадений"


def build_enstru_index(enstru_rows):
    index = {}
    for r in enstru_rows:
        tokens = (
            tokenize(r.get("name_rus")   or "")[:3] +
            tokenize(r.get("detail_rus") or "")[:2] +
            tokenize(r.get("standard")   or "")[:2]
        )
        seen = set()
        for t in tokens:
            if t not in seen:
                index.setdefault(t, []).append(r)
                seen.add(t)
    return index


def get_enstru_candidates(a, enstru_index):
    tokens = (
        tokenize(a.get("full_name") or "")[:4] +
        tokenize(a.get("name_ru")   or "")[:2] +
        tokenize(a.get("standart")  or "")[:2]
    )
    seen = set()
    result = []
    for t in tokens:
        for r in enstru_index.get(t, []):
            if r["code"] not in seen:
                seen.add(r["code"])
                result.append(r)
    return result


def create_result_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.agsk_enstru_exclusive (
            id              serial PRIMARY KEY,
            agsk_code       text        UNIQUE,   -- каждый agsk максимум один раз
            enstru_code     varchar(35) UNIQUE,   -- каждый enstru максимум один раз
            name_ru_agsk    text,
            agsk_full_name  text,
            name_ru_enstru  text,
            detail_enstru   text,
            standard_enstru text,
            score           int,
            reason          text,
            created_at      timestamp DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_excl_score ON public.agsk_enstru_exclusive (score DESC);
    """)


def insert_batch(cur, rows):
    if not rows:
        return
    psycopg2.extras.execute_values(cur, """
        INSERT INTO public.agsk_enstru_exclusive
            (agsk_code, enstru_code, name_ru_agsk, agsk_full_name,
             name_ru_enstru, detail_enstru, standard_enstru, score, reason)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, [
        (r["agsk_code"], r["enstru_code"], r["name_ru_agsk"], r["agsk_full_name"],
         r["name_ru_enstru"], r["detail_enstru"], r["standard_enstru"], r["score"], r["reason"])
        for r in rows
    ])


def main():
    if not PG["dbname"]:
        print("❌  Укажите PG_DB")
        sys.exit(1)

    print("🔌  Подключаемся к PostgreSQL...")
    conn = psycopg2.connect(**PG)
    conn.autocommit = False
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur_w = conn.cursor()

    print("🗄️   Создаём таблицу agsk_enstru_exclusive...")
    create_result_table(cur_w)
    cur_w.execute("TRUNCATE public.agsk_enstru_exclusive RESTART IDENTITY")
    conn.commit()

    # Загружаем всё в память — нужно для жадного алгоритма
    print("📥  Загружаем enstru...")
    cur.execute("""
        SELECT code, name_rus, detail_rus, standard, uom
        FROM public.enstru WHERE is_active = true
    """)
    enstru_rows  = [dict(r) for r in cur.fetchall()]
    enstru_index = build_enstru_index(enstru_rows)
    enstru_by_code = {r["code"]: r for r in enstru_rows}
    print(f"    enstru: {len(enstru_rows)} записей")

    print("📥  Загружаем agsk...")
    cur.execute("""
        SELECT code, name_ru, full_name, "group", standart, unit
        FROM public.agsk
    """)
    agsk_rows = [dict(r) for r in cur.fetchall()]
    print(f"    agsk: {len(agsk_rows)} записей\n")

    # ── Шаг 1: собираем все пары с их score ──────────────────────────────────
    print("🔍  Считаем score для всех пар...")
    start = time.time()
    all_pairs = []  # (score, agsk_code, enstru_code, reason)

    for i, a in enumerate(agsk_rows, 1):
        candidates = get_enstru_candidates(a, enstru_index)
        for e in candidates:
            sc, reason = score_pair(a, e)
            if sc >= MIN_SCORE:
                all_pairs.append((sc, a["code"], e["code"], reason))

        if i % 500 == 0 or i == len(agsk_rows):
            pct = int(i / len(agsk_rows) * 100)
            elapsed = time.time() - start
            eta = elapsed / i * (len(agsk_rows) - i)
            print(f"\r  {i}/{len(agsk_rows)} ({pct}%)  пар найдено: {len(all_pairs)}  "
                  f"осталось: ~{int(eta//60)}м {int(eta%60)}с   ", end="", flush=True)

    elapsed = time.time() - start
    print(f"\n  Подсчёт завершён за {int(elapsed//60)}м {int(elapsed%60)}с")
    print(f"  Всего кандидатных пар: {len(all_pairs)}\n")

    # ── Шаг 2: сортируем по score DESC ───────────────────────────────────────
    print("📊  Сортируем пары по score...")
    all_pairs.sort(key=lambda x: -x[0])

    # ── Шаг 3: жадное назначение — каждый enstru занимаем только раз ─────────
    print("🎯  Назначаем пары (жадный алгоритм)...")
    used_enstru = set()   # занятые enstru
    used_agsk   = set()   # agsk которым уже нашли пару
    assignments = []

    for sc, agsk_code, enstru_code, reason in all_pairs:
        if agsk_code in used_agsk:
            continue        # этому agsk уже нашли пару
        if enstru_code in used_enstru:
            continue        # этот enstru уже занят

        # Свободны оба — назначаем!
        used_agsk.add(agsk_code)
        used_enstru.add(enstru_code)

        a = next(r for r in agsk_rows if r["code"] == agsk_code)
        e = enstru_by_code[enstru_code]

        assignments.append({
            "agsk_code":       agsk_code,
            "enstru_code":     enstru_code,
            "name_ru_agsk":    a["name_ru"],
            "agsk_full_name":  a["full_name"],
            "name_ru_enstru":  e["name_rus"],
            "detail_enstru":   e["detail_rus"],
            "standard_enstru": e["standard"],
            "score":           sc,
            "reason":          reason,
        })

    print(f"  Назначено пар: {len(assignments)}")
    print(f"  agsk без пары: {len(agsk_rows) - len(used_agsk)}")
    print(f"  enstru не задействовано: {len(enstru_rows) - len(used_enstru)}\n")

    # ── Шаг 4: пишем в БД батчами ────────────────────────────────────────────
    print("💾  Записываем в БД...")
    for i in range(0, len(assignments), BATCH_SIZE):
        batch = assignments[i:i + BATCH_SIZE]
        insert_batch(cur_w, batch)
        conn.commit()
        print(f"\r  {min(i + BATCH_SIZE, len(assignments))}/{len(assignments)}", end="", flush=True)

    print(f"\n\n✅  Готово!")

    cur_w.execute("""
        SELECT
            count(*)                                          AS "Назначено пар",
            count(*) FILTER (WHERE score >= 80)              AS "score >= 80",
            count(*) FILTER (WHERE score BETWEEN 60 AND 79) AS "score 60-79",
            count(*) FILTER (WHERE score BETWEEN 40 AND 59) AS "score 40-59",
            round(avg(score), 1)                             AS "Средний score"
        FROM public.agsk_enstru_exclusive
    """)
    conn.commit()
    row = dict(zip([d[0] for d in cur_w.description], cur_w.fetchone()))
    print("\n── Статистика ──────────────────────────────")
    for k, v in row.items():
        print(f"   {k:30} {v}")
    print("────────────────────────────────────────────")
    print("\nПросмотр:")
    print("  SELECT * FROM public.agsk_enstru_exclusive ORDER BY score DESC LIMIT 100;")

    cur.close()
    cur_w.close()
    conn.close()


if __name__ == "__main__":
    main()