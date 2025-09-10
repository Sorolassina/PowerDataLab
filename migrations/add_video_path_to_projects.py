"""
Migration pour ajouter le champ video_path à la table projects
Exécuter ce script pour mettre à jour la base de données existante
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models.base import engine, SessionLocal

def add_video_path_column():
    """Ajoute la colonne video_path à la table projects"""
    try:
        with engine.connect() as connection:
            # Vérifier si la colonne existe déjà
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='projects' AND column_name='video_path'
            """))
            
            if result.fetchone():
                print("La colonne video_path existe déjà dans la table projects.")
                return True
            
            # Ajouter la colonne video_path
            connection.execute(text("""
                ALTER TABLE projects 
                ADD COLUMN video_path VARCHAR(255)
            """))
            
            connection.commit()
            print("Colonne video_path ajoutée avec succès à la table projects.")
            return True
            
    except Exception as e:
        print(f"Erreur lors de l'ajout de la colonne video_path: {e}")
        return False

if __name__ == "__main__":
    print("Début de la migration...")
    if add_video_path_column():
        print("Migration terminée avec succès!")
    else:
        print("Échec de la migration.")
