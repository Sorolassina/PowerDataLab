"""
Migration pour ajouter le champ video_path à la table articles
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models.base import engine

def upgrade():
    """Ajouter le champ video_path à la table articles"""
    with engine.connect() as conn:
        # Vérifier si la colonne existe déjà
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'articles' 
            AND column_name = 'video_path'
        """))
        
        if result.scalar() == 0:
            # Ajouter la colonne video_path
            conn.execute(text("ALTER TABLE articles ADD COLUMN video_path TEXT"))
            conn.commit()
            print("✅ Colonne video_path ajoutée à la table articles")
        else:
            print("ℹ️ La colonne video_path existe déjà dans la table articles")

def downgrade():
    """Supprimer le champ video_path de la table articles"""
    with engine.connect() as conn:
        # Vérifier si la colonne existe
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'articles' 
            AND column_name = 'video_path'
        """))
        
        if result.scalar() > 0:
            # Supprimer la colonne video_path
            conn.execute(text("ALTER TABLE articles DROP COLUMN video_path"))
            conn.commit()
            print("✅ Colonne video_path supprimée de la table articles")
        else:
            print("ℹ️ La colonne video_path n'existe pas dans la table articles")

if __name__ == "__main__":
    print("Migration: Ajout du champ video_path aux articles")
    upgrade()
