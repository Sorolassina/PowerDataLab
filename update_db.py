import sqlite3
import os

def update_database():
    db_path = 'blog.db'
    if not os.path.exists(db_path):
        print(f"Base de données {db_path} non trouvée")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Vérifier si la colonne is_blocked existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Ajouter les colonnes manquantes si nécessaire
        if 'is_blocked' not in columns:
            print("Ajout de la colonne is_blocked...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
        
        if 'reset_token' not in columns:
            print("Ajout de la colonne reset_token...")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        
        if 'reset_token_expiry' not in columns:
            print("Ajout de la colonne reset_token_expiry...")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP")
        
        conn.commit()
        print("Mise à jour de la base de données terminée avec succès!")
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base de données: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_database() 