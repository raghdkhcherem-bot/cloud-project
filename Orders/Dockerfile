# Utiliser une image Python officielle légère
FROM python:3.10-slim

# Définir le dossier de travail dans le conteneur
WORKDIR /app

# Copier et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code source
COPY . .

# Exposer le port interne du service
EXPOSE 5000

# Commande pour lancer l'application
CMD ["python", "app.py"]
