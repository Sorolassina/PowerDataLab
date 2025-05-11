from app import app, db
from models import User, Article, Category, NewsletterSubscriber
from werkzeug.security import generate_password_hash

def recreate_database():
    with app.app_context():
        # Supprimer toutes les tables existantes
        db.drop_all()
        print("Tables existantes supprimées.")
        
        # Recréer toutes les tables
        db.create_all()
        print("Tables recréées avec succès.")
        
        # Créer un utilisateur administrateur avec un nouveau mot de passe
        admin = User(
            username='admin',
            email='sorolassina58@gmail.com',
            password_hash=generate_password_hash('admin123'),  # Nouveau mot de passe
            is_verified_admin=False
        )
        db.session.add(admin)
        db.session.commit()
        print("Utilisateur administrateur créé avec le mot de passe 'admin123'")

if __name__ == '__main__':
    recreate_database() 