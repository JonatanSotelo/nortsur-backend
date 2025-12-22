import os
import sys
import sqlite3

# Asegurar imports desde /app (donde vive models.py)
APP_DIR = "/app"
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import models  # noqa: E402  (carga Base.metadata)

DB_PATH = os.getenv('SQLITE_PATH', '/app/data/nortsur.db')


def sqlite_type_for(coltype) -> str:
    t = str(coltype).upper()
    if 'INT' in t:
        return 'INTEGER'
    if 'BOOL' in t:
        return 'INTEGER'
    if 'REAL' in t or 'FLOAT' in t or 'NUM' in t or 'DECIMAL' in t:
        return 'REAL'
    if 'DATE' in t or 'TIME' in t:
        return 'TEXT'
    return 'TEXT'


def get_existing_columns(cur, table: str) -> set[str]:
    cur.execute(f'PRAGMA table_info({table})')
    return {row[1] for row in cur.fetchall()}


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f'DB no existe: {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    total_added = 0

    for table in models.Base.metadata.sorted_tables:
        table_name = table.name

        if not table_exists(cur, table_name):
            print(f'[SKIP] Tabla no existe en DB: {table_name}')
            continue

        existing = get_existing_columns(cur, table_name)

        for col in table.columns:
            col_name = col.name
            if col_name in existing:
                continue

            col_type = sqlite_type_for(col.type)

            ddl = f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}'
            cur.execute(ddl)
            conn.commit()
            total_added += 1
            print(f'[ADD] {table_name}.{col_name} {col_type}')

    print(f'OK: columnas agregadas: {total_added}')

    # ------------------------------------------------------------------
    # 🔹 BACKFILL DE TIMESTAMPS (PEGAR ESTO)
    # ------------------------------------------------------------------
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    if table_exists(cur, "pedidos"):
        cols = get_existing_columns(cur, "pedidos")

        if "creado_en" in cols:
            cur.execute(
                "UPDATE pedidos SET creado_en = COALESCE(creado_en, ?) "
                "WHERE creado_en IS NULL OR TRIM(creado_en)=''",
                (now,)
            )

        if "actualizado_en" in cols:
            cur.execute(
                "UPDATE pedidos SET actualizado_en = COALESCE(actualizado_en, ?) "
                "WHERE actualizado_en IS NULL OR TRIM(actualizado_en)=''",
                (now,)
            )

        conn.commit()

    # ------------------------------------------------------------------

    conn.close()



if __name__ == '__main__':
    main()
