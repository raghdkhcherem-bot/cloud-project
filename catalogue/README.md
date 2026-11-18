# Service Catalogue

Microservice de gestion des produits de la PME (cosmétiques naturels, huiles essentielles, savons artisanaux). Il fait partie de l'architecture du mini-projet Cloud Computing : Catalogue, Commandes, Notifications.

- **Langage / framework :** Python 3.11, Flask
- **Base de données :** PostgreSQL (base `db_catalogue`)
- **Port interne du conteneur :** 5000 (publié en **5001** sur la machine)
- **Nom sur le réseau Docker :** `catalogue`

## API

| Méthode | Route | Réponse |
|---|---|---|
| GET | `/products` | 200 : liste de tous les produits |
| GET | `/products/<id>` | 200 : un produit, ou 404 `{"error": "Produit introuvable"}` |
| GET | `/health` | 200 : `{"status": "ok"}` |

Exemple de produit :

```json
{
  "id": 1,
  "name": "Savon d'Alep artisanal",
  "price": 8.5,
  "stock": 40,
  "description": "Savon naturel à l'huile d'olive"
}
```

Au premier démarrage, la table `products` est créée et remplie avec 6 produits de test (ids 1 à 6).

## Configuration

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `DATABASE_URL` | URL de connexion PostgreSQL | `postgresql://postgres:postgres@localhost:5432/db_catalogue` |

Dans Docker Compose, la valeur est de la forme `postgresql://UTILISATEUR:MOT_DE_PASSE@db/db_catalogue`. Aucun mot de passe n'est écrit dans le code.

Le service réessaie de se connecter à la base pendant environ 40 secondes au démarrage : `depends_on` n'attend pas que PostgreSQL soit prêt.

## Appel depuis un autre service

Entre conteneurs, utiliser le nom du service et le port interne, jamais `localhost` :

```
http://catalogue:5000/products/<id>
```

## Lancer le service seul

Prérequis : Docker Desktop.

```bash
# 1. Réseau et base de données
docker network create app-net
docker run -d --name db --network app-net \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=db_catalogue \
  -v pgdata_test:/var/lib/postgresql/data postgres:16

# 2. Image et conteneur (depuis le dossier catalogue/)
docker build -t catalogue .
docker run -d --name catalogue --network app-net -p 5001:5000 \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/db_catalogue \
  catalogue
```

Tester : `http://localhost:5001/products`

Arrêter et nettoyer : `docker rm -f catalogue db`

Les identifiants `postgres` / `postgres` sont réservés aux tests locaux.

## Lancer sans Docker (développement)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py                # écoute sur http://localhost:5000
```

Une base PostgreSQL `db_catalogue` doit être accessible sur `localhost:5432`.

## Persistance

Les données sont stockées dans PostgreSQL, dont le dossier de données est monté sur un volume Docker. Supprimer puis recréer les conteneurs avec le même volume conserve les données.

## Contenu du dossier

```
catalogue/
├── app.py             # API Flask, accès à la base
├── requirements.txt   # flask, psycopg2-binary
├── Dockerfile         # image du service
└── .dockerignore
```
