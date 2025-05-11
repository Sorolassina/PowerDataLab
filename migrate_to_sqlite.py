import sqlite3
import os
from datetime import datetime

def create_tables(conn):
    cursor = conn.cursor()
    
    # Création des tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        color_theme TEXT DEFAULT '#000000',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        content TEXT NOT NULL,
        category_id INTEGER,
        user_id INTEGER,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        article_id INTEGER,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS newsletter_subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        confirmed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS newsletters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        content TEXT NOT NULL,
        sent_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS page_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        view_count INTEGER DEFAULT 0,
        last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles (id)
    )
    ''')

    conn.commit()

def insert_default_data(conn):
    cursor = conn.cursor()
    
    # Insérer les catégories par défaut
    categories = [
        ('Power BI', 'power-bi', '#F2C811', 'Analyse de données et visualisation avec Power BI'),
        ('Power Apps', 'power-apps', '#742774', 'Création d\'applications métier avec Power Apps'),
        ('Power Automate', 'power-automate', '#0066FF', 'Automatisation des processus métier avec Power Automate'),
        ('Power Virtual Agents', 'power-virtual-agents', '#00B7C3', 'Création de chatbots avec Power Virtual Agents'),
        ('SharePoint', 'sharepoint', '#217346', 'Gestion de contenu et collaboration avec SharePoint')
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO categories (name, slug, color_theme, description)
    VALUES (?, ?, ?, ?)
    ''', categories)
    
    # Insérer un utilisateur admin par défaut si aucun n'existe
    cursor.execute('''
    INSERT OR IGNORE INTO users (username, email, password_hash, is_admin)
    VALUES (?, ?, ?, ?)
    ''', ('admin', 'admin@example.com', 'change_this_password_hash', 1))
    
    conn.commit()

def main():
    db_path = 'blog.db'
    
    # Créer une nouvelle connexion à la base de données
    conn = sqlite3.connect(db_path)
    
    try:
        # Créer les tables
        create_tables(conn)
        
        # Insérer les données par défaut
        insert_default_data(conn)
        
        print("Migration terminée avec succès!")
        
    except Exception as e:
        print(f"Erreur lors de la migration : {e}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main() 