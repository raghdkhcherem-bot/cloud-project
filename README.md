# Cloudifier une PME e-business avec une architecture microservices

Mini-projet **Cloud Computing** – Novembre 2026

Modernisation du système d'information d'une PME tunisienne de vente en ligne de produits artisanaux et naturels (cosmétiques naturels, huiles essentielles, savons) : passage d'une infrastructure traditionnelle (serveur unique, base locale, sauvegardes manuelles) à une architecture **microservices** conteneurisée avec **Docker** et **Docker Compose**, pensée pour un **Cloud public**.

## Équipe

| Membre | Rôle |
|---|---|
| Ikram Elloumi | Membre 1 – Analyse et conception (Partie 1) |
| Zeineb Frikha | Membre 2 – Service Catalogue |
| Eya Achour | Membre 3 – Services Commandes et Notifications |
| Raghd Khecharem | Membre 4 – Project Manager, environnement Docker et déploiement Docker Compose |

## Architecture

Trois microservices indépendants, chacun avec son code, son Dockerfile, son API REST (JSON) et sa propre base PostgreSQL.

```
Client ──► Catalogue (5001)      ──► db_catalogue
       ──► Commandes (5002)      ──► db_commandes
                 │  ├─ GET /products/<id> ──► Catalogue
                 │  └─ POST /notify       ──► Notifications (5003) ──► db_notifications
```

| Service | Rôle | Port publié → interne | Base |
|---|---|---|---|
| `catalogue` | Consultation des produits | 5001 → 5000 | `db_catalogue` |
| `commandes` | Création et consultation des commandes, vérification du produit et du stock, déclenchement de la notification | 5002 → 5000 | `db_commandes` |
| `notifications` | Enregistrement des notifications (envoi d'e-mail simulé) | 5003 → 5000 | `db_notifications` |

- **Réseau Docker :** `pme-network` (bridge). Les services s'appellent par leur nom, par exemple `http://catalogue:5000`.
- **Bases de données :** trois conteneurs `postgres:16-alpine`, un par service, avec un healthcheck `pg_isready`.
- **Volumes :** `catalogue_data`, `commandes_data`, `notifications_data` (les données survivent à l'arrêt ou à la recréation des conteneurs).
- **Résilience :** `restart: unless-stopped` ; si Notifications est indisponible, la commande reste enregistrée et la réponse indique l'échec de la notification.

## Technologies

Python 3.11 · Flask · psycopg2 · PostgreSQL 16 · JSON / API REST · Docker · Docker Compose · GitHub

## Structure du dépôt

```
cloud-project/
├── catalogue/          # service Catalogue (app.py, requirements.txt, Dockerfile)
├── commandes/          # service Commandes (app.py, requirements.txt, Dockerfile)
├── notifications/      # service Notifications (app.py, requirements.txt, Dockerfile)
├── docker-compose.yml  # orchestration de l'ensemble
└── README.md
```

## Prérequis

- Docker Desktop (ou Docker Engine + plugin Compose)
- Git

Vérification :

```bash
docker --version
docker run hello-world
```

## Lancement

```bash
git clone https://github.com/raghdkhcherem-bot/cloud-project.git
cd cloud-project
docker compose up -d
```

Au démarrage, les trois bases passent à l'état *healthy*, puis les trois services démarrent. Le service Catalogue crée sa table `products` et y insère six produits de test.

Commandes utiles :

```bash
docker compose ps            # état des services (ou : docker ps)
docker compose logs          # journaux
docker volume ls             # volumes de données
docker compose down          # arrêt (les volumes sont conservés)
docker compose down -v       # arrêt et suppression des données
```

## API

Toutes les réponses sont au format JSON. Chaque service expose `GET /health` (réponse : `{"status": "ok"}`).

### Catalogue – http://localhost:5001

| Route | Description | Réponses |
|---|---|---|
| `GET /products` | Liste des produits | 200 |
| `GET /products/<id>` | Détail d'un produit | 200, 404 si inconnu |

### Commandes – http://localhost:5002

| Route | Description | Réponses |
|---|---|---|
| `POST /orders` | Crée une commande | 201, 400 données invalides, 404 produit inconnu, 409 stock insuffisant, 503 Catalogue injoignable |
| `GET /orders` | Liste des commandes | 200 |
| `GET /orders/<id>` | Détail d'une commande | 200 |

Corps attendu pour `POST /orders` : `product_id` (entier), `quantity` (entier > 0), `customer_name`, `customer_email`.

### Notifications – http://localhost:5003

| Route | Description | Réponses |
|---|---|---|
| `POST /notify` | Enregistre une notification (`order_id`, `customer_email`, `message`) | 201, 400 données invalides |
| `GET /notifications` | Historique des notifications | 200 |

## Exemple d'utilisation

```bash
# 1. Consulter le catalogue
curl http://localhost:5001/products

# 2. Passer une commande (2 savons d'Alep à 8,5 → total 17,0)
curl -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2, "customer_name": "Test", "customer_email": "test@example.com"}'

# 3. Vérifier la notification créée automatiquement
curl http://localhost:5003/notifications
```

> Sous PowerShell, utiliser `curl.exe` à la place de `curl`.

## Tests réalisés

- Liste et détail des produits, produit inconnu (404), route `/health`.
- Création d'une commande valide avec calcul du total et notification automatique.
- Cas d'erreur : produit inexistant (404), stock insuffisant (409), corps vide ou invalide (400).
- Persistance des commandes après redémarrage du service.
- Démarrage de toute la pile avec une seule commande (`docker compose up -d`).

## Conventions techniques

- Port interne **5000** pour les trois services ; ports publiés 5001, 5002, 5003.
- Configuration par variables d'environnement (par exemple `DATABASE_URL`) : aucun mot de passe dans le code.
- Route `GET /health` dans chaque service.
- Un dossier par service dans un dépôt commun.

## Limites et évolutions

- Prototype exécuté en local : pas encore déployé chez un fournisseur Cloud public (PaaS/IaaS, puis DBaaS pour PostgreSQL).
- Non réalisés : ajout, modification et suppression de produits (BF02), analyse des clients (BF06), envoi réel d'e-mails, interface web, authentification, HTTPS.
- Supervision limitée aux routes `/health` et aux healthchecks ; sauvegardes automatisées à mettre en place.
- Le Dockerfile du service Commandes utilise `python:3.10-slim`, les autres `python:3.11-slim` : à harmoniser.
- Migration des données de la base MySQL actuelle vers PostgreSQL à planifier.

## Documentation

Le rapport complet (diagnostic, comparaison des modèles Cloud, conception, développement, déploiement, conclusion et glossaire) se trouve dans `Rapport_finale_corrige.docx`.
