import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/db_catalogue",
)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db(retries=20, delay=2):
    # depends_on ne garantit pas que PostgreSQL est prêt : on réessaie
    conn = None
    for _ in range(retries):
        try:
            conn = get_conn()
            break
        except psycopg2.OperationalError:
            time.sleep(delay)
    if conn is None:
        raise RuntimeError("Base de données inaccessible")

    with conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                stock INTEGER NOT NULL,
                description TEXT
            )
        """)
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO products (name, price, stock, description) VALUES (%s, %s, %s, %s)",
                [
                    ("Savon d'Alep artisanal", 8.5, 40, "Savon naturel à l'huile d'olive"),
                    ("Savon au miel", 6.0, 60, "Savon doux pour peaux sensibles"),
                    ("Huile essentielle de lavande", 18.0, 25, "Flacon de 10 ml, 100 % naturelle"),
                    ("Huile essentielle d'eucalyptus", 16.5, 30, "Flacon de 10 ml"),
                    ("Huile d'argan cosmétique", 35.0, 15, "Huile pure pour peau et cheveux"),
                    ("Crème au beurre de karité", 22.0, 20, "Crème hydratante naturelle"),
                ],
            )
    conn.close()


@app.route("/products", methods=["GET"])
def list_products():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products ORDER BY id")
        rows = cur.fetchall()
    return jsonify(rows)


@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        row = cur.fetchone()
    if row is None:
        return jsonify({"error": "Produit introuvable"}), 404
    return jsonify(row)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)