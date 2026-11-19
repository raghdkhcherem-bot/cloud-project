import os
import time

import psycopg2
import requests
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

CATALOGUE_URL = os.environ.get("CATALOGUE_URL", "http://catalogue:5000")
NOTIFICATIONS_URL = os.environ.get("NOTIFICATIONS_URL", "http://notifications:5000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/db_commandes",
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
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
    conn.close()


def serialiser(row):
    # jsonify ne sait pas écrire un datetime proprement : on le convertit en texte
    row = dict(row)
    if row.get("created_at"):
        row["created_at"] = row["created_at"].isoformat()
    return row


@app.route("/")
def accueil():
    return "Bienvenue dans le microservice Commandes !"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/orders", methods=["POST"])
def creer_commande():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Corps JSON requis"}), 400

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    customer_name = data.get("customer_name")
    customer_email = data.get("customer_email")

    if not isinstance(product_id, int) or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "product_id et quantity doivent être des entiers, quantity > 0"}), 400
    if not customer_name or not customer_email:
        return jsonify({"error": "customer_name et customer_email requis"}), 400

    # 1. Vérification auprès du service Catalogue (Membre 2)
    try:
        response = requests.get(f"{CATALOGUE_URL}/products/{product_id}", timeout=5)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Impossible de joindre le service Catalogue"}), 503

    if response.status_code == 404:
        return jsonify({"error": "Produit introuvable"}), 404
    if response.status_code != 200:
        return jsonify({"error": "Erreur du service Catalogue"}), 502

    product = response.json()
    if product["stock"] < quantity:
        return jsonify({"error": "Stock insuffisant", "stock_disponible": product["stock"]}), 409

    total = round(product["price"] * quantity, 2)

    # 2. Enregistrement de la commande dans PostgreSQL
    try:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO orders (product_id, quantity, total, status, customer_name, customer_email)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (product_id, quantity, total, "confirmée", customer_name, customer_email),
            )
            commande = cur.fetchone()
    except psycopg2.Error:
        return jsonify({"error": "Impossible d'enregistrer la commande"}), 500

    resultat = serialiser(commande)

    # 3. Demande de notification au service Notifications
    # Si les notifications sont indisponibles, la commande reste valide.
    try:
        notif = requests.post(
            f"{NOTIFICATIONS_URL}/notify",
            json={
                "order_id": resultat["id"],
                "customer_email": customer_email,
                "message": f"Votre commande {resultat['id']} est confirmée (total : {total})",
            },
            timeout=5,
        )
        resultat["notification"] = "envoyée" if notif.status_code == 201 else "échec"
    except requests.exceptions.RequestException:
        resultat["notification"] = "échec"

    return jsonify(resultat), 201


@app.route("/orders", methods=["GET"])
def lister_commandes():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM orders ORDER BY id")
        rows = cur.fetchall()
    return jsonify([serialiser(r) for r in rows])


@app.route("/orders/<int:order_id>", methods=["GET"])
def get_commande(order_id):
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        row = cur.fetchone()
    if row is None:
        return jsonify({"error": "Commande introuvable"}), 404
    return jsonify(serialiser(row))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
