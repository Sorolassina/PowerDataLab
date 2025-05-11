from app import app, db
import sqlite3

def get_admin_hash():
    with app.app_context():
        conn = sqlite3.connect('instance/blog.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT password_hash FROM user WHERE email = ?', ('sorolassina58@gmail.com',))
            result = cursor.fetchone()
            if result:
                print(f"Hash trouvé : {result[0]}")
            else:
                print("Aucun hash trouvé pour l'administrateur.")
        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    get_admin_hash() 