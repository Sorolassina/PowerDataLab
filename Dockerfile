# Étape 1 : base Python
FROM python:3.11-slim

# Étape 2 : définition du répertoire de travail
WORKDIR /app

# Étape 3 : copier les fichiers dans l'image
COPY . /app

# Étape 4 : installer les dépendances
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Étape 5 : exposer le port
EXPOSE 8050

# Étape 6 : lancer l'app Flask avec le fichier .env
#CMD ["sh", "-c", "python -m dotenv.cli && alembic upgrade head && python app.py"]
#CMD ["sh", "-c", "alembic upgrade head && python app.py"]
CMD ["sh", "-c", "alembic stamp head && python app.py"]

 
