import os
import time

import psycopg2
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5434/db_notifications",
)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db(retries=20, delay=2):
    # PostgreSQL peut mettre quelques secondes à démarrer : on réessaie
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
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                customer_email TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
    conn.close()


def serialiser(row):
    row = dict(row)
    if row.get("created_at"):
        row["created_at"] = row["created_at"].isoformat()
    return row


@app.route("/")
def accueil():
    return "Bienvenue dans le microservice Notifications !"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/notify", methods=["POST"])
def notifier():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Corps JSON requis"}), 400

    order_id = data.get("order_id")
    customer_email = data.get("customer_email")
    message = data.get("message")

    if not isinstance(order_id, int):
        return jsonify({"error": "order_id doit être un entier"}), 400
    if not customer_email or not message:
        return jsonify({"error": "customer_email et message requis"}), 400

    # Envoi simulé : on enregistre la notification avec le statut "envoyée"
    try:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO notifications (order_id, customer_email, message, status)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (order_id, customer_email, message, "envoyée"),
            )
            notification = cur.fetchone()
    except psycopg2.Error:
        return jsonify({"error": "Impossible d'enregistrer la notification"}), 500

    return jsonify(serialiser(notification)), 201


@app.route("/notifications", methods=["GET"])
def lister_notifications():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM notifications ORDER BY id")
        rows = cur.fetchall()
    return jsonify([serialiser(r) for r in rows])


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))