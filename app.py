from flask import Flask,  request,  url_for,  session, jsonify,  g
from flask_login import LoginManager,  login_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_mail import Mail
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import  func
from models.base import engine, SessionLocal, Base, get_db  # Import modifié
from models import Article, Category
from sqlalchemy.orm import scoped_session
from models import Base,  Article, Category
from utils.verif_image import allowed_file
from routes import blueprints
from utils.decorateur import login_required, admin_required
from models.user import User

# Chargement des variables d'environnement
load_dotenv()
print("Variables d'environnement chargées :")
print(f"FLASK_ENV: {os.environ.get('FLASK_ENV')}")
print(f"MAIL_SERVER: {os.environ.get('MAIL_SERVER')}")
print(f"MAIL_PORT: {os.environ.get('MAIL_PORT')}")
print(f"MAIL_USE_TLS: {os.environ.get('MAIL_USE_TLS')}")
print(f"MAIL_USERNAME: {os.environ.get('MAIL_USERNAME')}")
print(f"MAIL_PASSWORD: {'Présent' if os.environ.get('MAIL_PASSWORD') else 'Manquant'}")
print(f"MAIL_DEFAULT_SENDER: {os.environ.get('MAIL_DEFAULT_SENDER')}")

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key-here'),
    UPLOAD_FOLDER='/app/static/uploads',  # Chemin absolu pour Render
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    WTF_CSRF_ENABLED=True,
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
)

# Configuration CSRF
csrf = CSRFProtect(app)
db_session = scoped_session(SessionLocal)
# Créer les tables si elles n'existent pas
Base.metadata.create_all(engine)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

def init_db():
    """Initialise la base de données avec les catégories par défaut si nécessaire."""
    try:
        # Vérifier si les catégories existent déjà
        categories_count = db_session.query(Category).count()
        if categories_count == 0:
            print("Création des catégories par défaut...")
            # Définir les catégories par défaut
            categories = {
                'power-bi': {
                    'name': 'Power BI',
                    'color': '#F2C811',
                    'description': 'Analyse de données et visualisation avec Power BI'
                },
                'power-apps': {
                    'name': 'Power Apps',
                    'color': '#742774',
                    'description': 'Création d\'applications métier avec Power Apps'
                },
                'power-automate': {
                    'name': 'Power Automate',
                    'color': '#0066FF',
                    'description': 'Automatisation des processus métier avec Power Automate'
                },
                'sharepoint': {
                    'name': 'SharePoint',
                    'color': '#217346',
                    'description': 'Gestion de contenu et collaboration avec SharePoint'
                },
                'divers': {
                    'name': 'Divers',
                    'color': '#de0218',
                    'description': 'Articles divers et variés'
                }
            }
            
            # Créer les catégories
            for slug, data in categories.items():
                category = Category(
                    name=data['name'],
                    slug=slug,
                    color_theme=data['color'],
                    description=data['description']
                )
                db_session.add(category)
            
            db_session.commit()
            print("Catégories créées avec succès !")
        else:
            print("Catégories existantes détectées.")
    except Exception as e:
        db_session.rollback()
        print(f"Erreur lors de l'initialisation de la base de données : {e}")

# Initialisation des extensions
mail = Mail()
mail.init_app(app)
app.mail = mail  # Rendre mail accessible via current_app

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'

# Création des dossiers nécessaires
print(f"[DEBUG] Création du dossier d'upload : {app.config['UPLOAD_FOLDER']}")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
print(f"[DEBUG] Dossier d'upload créé avec succès")

def is_admin():
    return session.get('is_admin', False)

# Ajouter ce décorateur
@app.before_request
def before_request():
    print(f"[DEBUG] Nouvelle requête: {request.method} {request.path}")
    print(f"[DEBUG] Form data: {request.form}")
    print(f"[DEBUG] CSRF Token from form: {request.form.get('csrf_token')}")
    print(f"[DEBUG] Session CSRF token: {session.get('csrf_token')}")
    g.db = SessionLocal()

@app.after_request
def after_request(response):
    print(f"[DEBUG] Réponse status code: {response.status_code}")
    if response.status_code == 400:
        print(f"[DEBUG] Bad Request Details: {response.get_data(as_text=True)}")
    return response

# Routes principales
@app.before_request
def load_categories():
    if 'categories' not in g:
        # Récupérer les catégories avec leur nombre d'articles
        categories = g.db.query(
            Category,
            func.count(Article.id).label('article_count')
        ).outerjoin(
            Article, Category.id == Article.category_id
        ).group_by(Category.id).all()
        
        # Transformer les résultats en liste de dictionnaires
        categories_list = []
        for category, count in categories:
            category_dict = {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'color_theme': category.color_theme,
                'description': category.description,
                'article_count': count
            }
            categories_list.append(category_dict)
        
        g.categories = categories_list

@app.context_processor
def inject_categories():
    return dict(categories=g.get('categories', []))

class CSRFProtectForm(FlaskForm):
    pass

@app.route('/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    """Route pour l'upload d'images via TinyMCE"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Générer un nom de fichier unique
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Créer le dossier uploads s'il n'existe pas
            upload_folder = os.path.join(app.static_folder, 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Sauvegarder le fichier
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            # Retourner l'URL de l'image pour TinyMCE
            image_url = url_for('static', filename=f'uploads/{unique_filename}')
            return jsonify({
                'location': image_url
            })
        except Exception as e:
            app.logger.error(f"Erreur lors de l'upload d'image: {str(e)}")
            return jsonify({'error': 'Erreur lors de l\'upload de l\'image'}), 500
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/get-csrf-token')
def get_csrf_token():
    """Route pour obtenir un nouveau token CSRF"""
    return jsonify({'csrf_token': generate_csrf()})

@login_manager.user_loader
def load_user(user_id):
    return g.db.query(User).get(int(user_id))

@app.teardown_request
def teardown_request(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Enregistre tous les modules de routes (articles, catégories, auth, etc.)
for blueprint in blueprints:
    app.register_blueprint(blueprint)
    print(f"Blueprint enregistré: {blueprint.name}")

if __name__ == '__main__':
    with app.app_context():
        # Initialiser la base de données
        init_db()
    
    # Déterminer le port en fonction de l'environnement
    port = int(os.getenv('PORT', 8050))
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    app.run(host=host, port=port, debug=(os.getenv('FLASK_ENV') != 'production'))