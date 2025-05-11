from app import app, db
from models import User, Category, Article, Comment, NewsletterSubscriber

def reset_db():
    with app.app_context():
        # Supprimer toutes les tables
        db.drop_all()
        
        # Recréer toutes les tables
        db.create_all()
        
        # Créer les catégories de la Power Platform
        categories = [
            Category(name='Power BI', slug='power-bi', color='#F2C811'),
            Category(name='Power Apps', slug='power-apps', color='#742774'),
            Category(name='Power Automate', slug='power-automate', color='#0066FF'),
            Category(name='Power Virtual Agents', slug='power-virtual-agents', color='#00B7C3'),
            Category(name='Power Pages', slug='power-pages', color='#217346'),
            Category(name='Power Platform', slug='power-platform', color='#0078D4')
        ]
        
        for category in categories:
            db.session.add(category)
        
        db.session.commit()
        print("Base de données réinitialisée avec succès !")

def init_db():
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    # Ajouter les catégories par défaut
    categories = [
        {'name': 'Power BI', 'slug': 'power-bi', 'color': '#F2C811'},
        {'name': 'Power Apps', 'slug': 'power-apps', 'color': '#742774'},
        {'name': 'Power Automate', 'slug': 'power-automate', 'color': '#0066FF'},
        {'name': 'Power Virtual Agents', 'slug': 'power-virtual-agents', 'color': '#00B7C3'},
        {'name': 'Power Pages', 'slug': 'power-pages', 'color': '#217346'},
        {'name': 'Power Platform', 'slug': 'power-platform', 'color': '#0078D4'}
    ]
    
    for category in categories:
        db.execute('INSERT INTO categories (name, slug, color_theme) VALUES (?, ?, ?)',
                  [category['name'], category['slug'], category['color']])
    
    db.commit()

if __name__ == '__main__':
    reset_db() 