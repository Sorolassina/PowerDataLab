#!/bin/bash

echo "Initialisation de la base de données..."
python -c "from app import app, db; app.app_context().push(); db.create_all()"
echo "Démarrage de l'application..."
exec "$@" 