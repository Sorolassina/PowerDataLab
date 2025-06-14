from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

"""# Configuration de la base de données
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Configuration pour Render (production)
    engine = create_engine(DATABASE_URL)
else:
    # Configuration locale
    DB_NAME = os.environ.get('DB_NAME', 'blog')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)
"""
# Nouvelle logique de configuration de la base de données
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    print(f"[PROD/RENDER] Utilisation de DATABASE_URL : {DATABASE_URL}")
else:
    DB_NAME = os.environ.get('DB_NAME', 'powerdatalab')
    DB_USER = os.environ.get('DB_USER', 'pdluser')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '2311SLSS')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development').lower()
    if FLASK_ENV == 'production':
        DB_HOST = os.environ.get('DB_HOST', 'db')
        print(f"Mode production - Utilisation de DB_HOST: {DB_HOST}")
    else:
        DB_HOST = os.environ.get('DB_HOST_DEV', 'localhost')
        print(f"Mode développement - Utilisation de DB_HOST_DEV: {DB_HOST}")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)
    print(f"[DEV/LOCAL] DATABASE_URL: {DATABASE_URL}")

# Créer une session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Créer une classe de base pour les modèles
Base = declarative_base()

# Fonction utilitaire pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 