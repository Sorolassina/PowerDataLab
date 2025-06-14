# Utiliser une image Python officielle
FROM python:3.11-slim-bullseye

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Créer le dossier uploads s'il n'existe pas
RUN mkdir -p static/uploads

# Exposer le port
EXPOSE 8050

# Commande pour démarrer l'application
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "app:app"]

 
