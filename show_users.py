from app import app, db, User
from datetime import datetime
import os

def format_date(date):
    if date:
        return date.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def show_users():
    try:
        print("Démarrage de l'affichage des utilisateurs...")
        print(f"Chemin de travail actuel : {os.getcwd()}")
        
        with app.app_context():
            print("Connexion à la base de données...")
            users = User.query.all()
            print(f"Nombre d'utilisateurs trouvés : {len(users)}")
            
            print("\nListe des utilisateurs enregistrés :")
            print("-" * 80)
            print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Admin':<10} {'Créé le':<20}")
            print("-" * 80)
            
            for user in users:
                print(f"{user.id:<5} {user.username:<20} {user.email:<30} {str(user.is_admin):<10} {format_date(user.created_at):<20}")
                
    except Exception as e:
        print(f"Une erreur s'est produite : {str(e)}")
        print("Type d'erreur :", type(e).__name__)
        import traceback
        print("Traceback complet :")
        print(traceback.format_exc())

if __name__ == '__main__':
    show_users() 