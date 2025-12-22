import sqlite3

DB_PATH = "data/nortsur.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Crear tabla nueva con CHECK
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pedidos_new (
        id INTEGER PRIMARY KEY,
        cliente_id INTEGER NOT NULL,
        fecha_creacion DATETIME,
        canal VARCHAR NOT NULL,
        estado VARCHAR NOT NULL DEFAULT 'NUEVO'
            CHECK (estado IN ('NUEVO','CONFIRMADO','ENTREGADO','CANCELADO')),
        total_bruto_cent BIGINT NOT NULL,
        descuento_cliente FLOAT,
        total_descuento_cent BIGINT NOT NULL,
        total_neto_cent BIGINT NOT NULL,
        observaciones VARCHAR,
        FOREIGN KEY(cliente_id) REFERENCES clientes (id)
    );
    """)

    # 2) Copiar datos desde pedidos -> pedidos_new
    cur.execute("""
    INSERT INTO pedidos_new (
        id, cliente_id, fecha_creacion, canal, estado,
        total_bruto_cent, descuento_cliente, total_descuento_cent, total_neto_cent,
        observaciones
    )
    SELECT
        id, cliente_id, fecha_creacion, canal, estado,
        total_bruto_cent, descuento_cliente, total_descuento_cent, total_neto_cent,
        observaciones
    FROM pedidos;
    """)

    # 3) Borrar tabla vieja y renombrar
    cur.execute("DROP TABLE pedidos;")
    cur.execute("ALTER TABLE pedidos_new RENAME TO pedidos;")

    conn.commit()
    conn.close()
    print("OK: CHECK constraint aplicado a pedidos.estado")

if __name__ == "__main__":
    main()

