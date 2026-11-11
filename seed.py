import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def poblar():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "auditoria_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgrespassword"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )
    cur = conn.cursor()

    # 1. Habilitar extensión vector en PostgreSQL
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Crear tabla de órdenes de compra
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ordenes_compra (
            id VARCHAR(50) PRIMARY KEY,
            proveedor_nombre VARCHAR(150),
            rif_proveedor VARCHAR(50),
            monto_aprobado NUMERIC(12, 2),
            moneda VARCHAR(10),
            tipo_compra VARCHAR(50),
            estado VARCHAR(50)
        );
    """)

    # 3. Insertar registros de prueba
    datos = [
        ("OC-2024-001", "Servicios Cloud AWS C.A.", "J-30123456-1", 1200.00, "USD", "Servicios", "APROBADA"),
        ("OC-2024-002", "Hardware & Redes Global", "J-40987654-2", 450.00, "USD", "Bienes", "APROBADA"),
        ("OC-2024-003", "Papelería e Insumos Caracas", "J-50111222-3", 80.00, "USD", "Bienes", "CANCELADA")
    ]

    cur.executemany("""
        INSERT INTO ordenes_compra (id, proveedor_nombre, rif_proveedor, monto_aprobado, moneda, tipo_compra, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """, datos)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Base de datos configurada y registros cargados con éxito.")

if __name__ == "__main__":
    poblar()