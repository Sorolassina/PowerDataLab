from app import app, db
import sqlite3

def update_database():
    with app.app_context():
        # Connexion à la base de données SQLite
        conn = sqlite3.connect('instance/blog.db')
        cursor = conn.cursor()
        
        try:
            # Ajouter la colonne is_verified_admin si elle n'existe pas
            cursor.execute('''
                ALTER TABLE user 
                ADD COLUMN is_verified_admin BOOLEAN DEFAULT FALSE
            ''')
            conn.commit()
            print("Base de données mise à jour avec succès !")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("La colonne existe déjà.")
            else:
                print(f"Erreur lors de la mise à jour : {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    update_database() 