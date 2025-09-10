#!/usr/bin/env python3
"""
Script de migration pour ajouter la colonne video_path à la table projects
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Configuration de la base de données
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'powerdatalab',
    'user': 'pdluser',
    'password': '2311SLSS'
}

def add_video_path_column():
    """Ajoute la colonne video_path à la table projects"""
    try:
        # Connexion à la base de données
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Vérifier si la colonne existe déjà
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='video_path'
        """)
        
        if cursor.fetchone():
            print("✅ La colonne video_path existe déjà dans la table projects.")
            return True
        
        # Ajouter la colonne video_path
        cursor.execute("""
            ALTER TABLE projects 
            ADD COLUMN video_path VARCHAR(255)
        """)
        
        conn.commit()
        print("✅ Colonne video_path ajoutée avec succès à la table projects.")
        
        # Vérifier que la colonne a été ajoutée
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='video_path'
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Vérification: colonne {result[0]} de type {result[1]} créée.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de la colonne video_path: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🚀 Début de la migration...")
    print("📊 Ajout de la colonne video_path à la table projects...")
    
    if add_video_path_column():
        print("🎉 Migration terminée avec succès!")
        print("🔄 Vous pouvez maintenant redémarrer votre application Flask.")
    else:
        print("💥 Échec de la migration.")
        sys.exit(1)
