import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    # Supprimer la base de données existante si elle existe
    if os.path.exists('blog.db'):
        os.remove('blog.db')

    # Créer une nouvelle connexion à la base de données
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row

    # Lire et exécuter le schéma SQL
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())

    # Créer un utilisateur admin par défaut
    admin_password = generate_password_hash('admin123')
    conn.execute('''
        INSERT INTO users (username, email, password_hash, is_admin)
        VALUES (?, ?, ?, ?)
    ''', ['admin', 'admin@example.com', admin_password, 1])

    # Créer les catégories par défaut
    categories = [
        ('Power BI', 'power-bi', '#F2C811', 'Analyse de données et visualisation avec Power BI'),
        ('Power Apps', 'power-apps', '#742774', 'Création d\'applications métier avec Power Apps'),
        ('Power Automate', 'power-automate', '#0066FF', 'Automatisation des processus métier avec Power Automate'),
        ('Power Virtual Agents', 'power-virtual-agents', '#00B7C3', 'Création de chatbots avec Power Virtual Agents'),
        ('SharePoint', 'sharepoint', '#217346', 'Gestion de contenu et collaboration avec SharePoint')
    ]

    for name, slug, color, description in categories:
        conn.execute('''
            INSERT INTO categories (name, slug, color_theme, description)
            VALUES (?, ?, ?, ?)
        ''', [name, slug, color, description])

    # Valider les changements et fermer la connexion
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Base de données initialisée avec succès!") 