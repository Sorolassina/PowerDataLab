from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import csv
from io import TextIOWrapper, StringIO
from flask_mail import Mail, Message
from dotenv import load_dotenv
import secrets
from PIL import Image
import json
from slugify import slugify
from functools import wraps
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo
import uuid
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import create_engine, func, and_, or_, desc, text
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, User, Article, Category, Comment, Newsletter, NewsletterSubscriber, NewsletterHistory, PageView
import re
from bleach import clean
import html2text

# Fonction pour vérifier les extensions de fichiers autorisées
def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    UPLOAD_FOLDER='static/uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_SECRET_KEY=os.environ.get('WTF_CSRF_SECRET_KEY', os.environ.get('SECRET_KEY')),
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
)

# Configuration CSRF
csrf = CSRFProtect(app)

# Configuration de la base de données
DB_NAME = os.environ.get('DB_NAME', 'powerdatalab')
DB_USER = os.environ.get('DB_USER', 'pdluser')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '2311SLSS')
DB_PORT = os.environ.get('DB_PORT', '5432')

# Sélection du host selon l'environnement
FLASK_ENV = os.environ.get('FLASK_ENV', 'development').lower()
if FLASK_ENV == 'production':
    DB_HOST = 'db'
    print(f"Mode production - Utilisation de DB_HOST: {DB_HOST}")
else:
    DB_HOST = 'localhost'
    print(f"Mode développement - Utilisation de DB_HOST_DEV: {DB_HOST}")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"DATABASE_URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(bind=engine))

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
mail = Mail(app)

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db_session.query(User).get(int(user_id))

# Création des dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Fonctions de gestion des utilisateurs
def get_user_by_id(user_id):
    return db_session.query(User).filter_by(id=user_id).first()

def get_user_by_email(email):
    return db_session.query(User).filter_by(email=email).first()

def create_user(username, email, password, is_admin=False):
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
        is_blocked=False
    )
    db_session.add(user)
    db_session.commit()
    return user

def update_user(user_id, **kwargs):
    user = db_session.query(User).filter_by(id=user_id).first()
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db_session.commit()
        return True
    return False

def delete_user(user_id):
    user = db_session.query(User).filter_by(id=user_id).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return True
    return False

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Mot de passe', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Mot de passe', validators=[DataRequired()])
    confirm_password = StringField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])

@app.route('/')
def index():
    # Récupérer les articles avec leurs relations
    articles = db_session.query(
        Article,
        Category.name.label('category_name'),
        Category.slug.label('category_slug'),
        Category.color_theme,
        User.username.label('author_name'),
        func.to_char(Article.created_at, 'DD/MM/YYYY').label('created_at_formatted')
    ).join(
        Category, Article.category_id == Category.id, isouter=True
    ).join(
        User, Article.author_id == User.id, isouter=True
    ).order_by(Article.created_at.desc()).all()
    
    # Transformer les résultats en dictionnaires pour faciliter l'accès dans le template
    articles_list = []
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    
    for article_row in articles:
        # Nettoyer le HTML et convertir en texte brut
        clean_content = clean(article_row.Article.content, strip=True)
        plain_text = h.handle(clean_content)
        
        # Créer le résumé
        excerpt = plain_text[:200] + '...' if len(plain_text) > 200 else plain_text
        
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'slug': article_row.Article.slug,
            'content': article_row.Article.content,
            'excerpt': excerpt,
            'image_path': article_row.Article.image_path,
            'created_at': article_row.Article.created_at,
            'created_at_formatted': article_row.created_at_formatted,
            'category_name': article_row.category_name,
            'category_slug': article_row.category_slug,
            'color_theme': article_row.color_theme,
            'author_name': article_row.author_name
        }
        articles_list.append(article_dict)
    
    return render_template('blog.html', articles=articles_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Gestion AJAX admin
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            is_admin = data.get('is_admin', False)
            admin_email = app.config.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_DEFAULT_SENDER')
            if is_admin and email and email == admin_email:
                session_code = generate_session_code()
                session['admin_code'] = session_code
                session['admin_code_expiry'] = datetime.now().replace(tzinfo=None) + timedelta(minutes=15)
                session['admin_email'] = email
                if send_admin_verification_email(email, session_code):
                    flash('Un code de vérification a été envoyé à votre adresse email. Veuillez le saisir sur la page suivante.', 'info')
                    return jsonify({'success': True, 'message': 'Code de vérification envoyé avec succès'})
                else:
                    flash('Erreur lors de l\'envoi du code de vérification. Veuillez réessayer.', 'error')
                    return jsonify({'success': False, 'message': "Erreur lors de l'envoi du code de vérification. Veuillez réessayer."}), 500
            else:
                flash('Email administrateur non reconnu. Veuillez vérifier votre adresse email.', 'error')
                return jsonify({'success': False, 'message': "Email administrateur non reconnu. Veuillez vérifier votre adresse email."}), 400
        # Logique classique utilisateur
        email = request.form['email']
        password = request.form['password']
        error = None
        user = db_session.query(User).filter_by(email=email).first()
        if user is None:
            error = 'Aucun compte ne correspond à cette adresse email. Veuillez vérifier votre saisie ou créer un compte.'
        elif not check_password_hash(user.password_hash, password):
            error = 'Le mot de passe saisi est incorrect. Veuillez réessayer ou utiliser la fonction "Mot de passe oublié".'
        elif user.is_blocked:
            error = 'Votre compte a été temporairement bloqué. Veuillez contacter l\'administrateur pour plus d\'informations.'
        if error is None:
            login_user(user)
            session['is_admin'] = user.is_admin
            flash(f'Bienvenue {user.username} ! Vous êtes maintenant connecté.', 'success')
            return redirect(url_for('index'))
        if error:
            flash(error, 'error')
            # Ajouter un message d'aide si l'email existe mais le mot de passe est incorrect
            if user is not None and not check_password_hash(user.password_hash, password):
                flash('Si vous avez oublié votre mot de passe, vous pouvez le réinitialiser en cliquant sur "Mot de passe oublié".', 'info')
    form = LoginForm()
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        error = None

        if db_session.query(User).filter_by(email=email).first():
            error = 'Un compte avec cet email existe déjà.'
        elif db_session.query(User).filter_by(username=username).first():
            error = 'Ce nom d\'utilisateur est déjà pris.'

        if error is None:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False,
                is_blocked=False
            )
            db_session.add(user)
            db_session.commit()
            
            # Envoyer l'email de bienvenue
            try:
                msg = Message(
                    subject="Bienvenue sur PowerDataLab !",
                    recipients=[email],
                    html=render_template('email/welcome.html',
                                       username=username,
                                       login_url=url_for('login', _external=True),
                                       now=datetime.now())  # Ajout de la variable now
                )
                mail.send(msg)
                flash('Un email de bienvenue vous a été envoyé !', 'success')
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email de bienvenue : {e}")
                # On continue même si l'email échoue
            
            login_user(user)
            flash('Compte créé avec succès!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

def is_admin():
    return session.get('is_admin', False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Accès non autorisé.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes principales
@app.route('/about')
def about():
    # Enregistrer la visite
    page_view = PageView(
        page='about',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        is_bot=1 if request.user_agent.browser is None else 0,
        viewed_at=datetime.now()
    )
    db_session.add(page_view)
    db_session.commit()
    
    # Envoyer une notification par email si c'est une visite humaine et que ce n'est pas l'admin connecté
    if page_view.is_bot == 0 and (not current_user.is_authenticated or current_user.email != os.getenv('MAIL_USERNAME')):
        try:
            msg = Message(
                subject="Nouvelle visite sur votre page À propos",
                recipients=[os.getenv('MAIL_USERNAME')],
                html=f"""
                <h2>Nouvelle visite sur votre page À propos</h2>
                <p>Une nouvelle personne a visité votre page À propos.</p>
                <ul>
                    <li>Date et heure : {page_view.viewed_at}</li>
                    <li>Navigateur : {request.user_agent.browser}</li>
                    <li>Plateforme : {request.user_agent.platform}</li>
                    <li>Provenance : {request.referrer or 'Accès direct'}</li>
                </ul>
                """
            )
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    return render_template('about.html')

@app.route('/category/<slug>')
def category(slug):
    category = db_session.query(Category).filter_by(slug=slug).first()
    if category is None:
        flash('Catégorie non trouvée.', 'error')
        return redirect(url_for('index'))
        
    articles = db_session.query(Article).filter_by(category_id=category.id).order_by(Article.created_at.desc()).all()
    categories = db_session.query(Category).all()
    
    # Enregistrer la visite
    page_view = PageView(
        page='category',
        page_id=None,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        is_bot=1 if request.user_agent.browser is None else 0,
        viewed_at=datetime.now()
    )
    db_session.add(page_view)
    db_session.commit()
    
    # Envoyer une notification si c'est une visite humaine et que ce n'est pas l'admin connecté
    if page_view.is_bot == 0 and (not current_user.is_authenticated or current_user.email != os.getenv('MAIL_USERNAME')):
        try:
            msg = Message(
                subject=f"Nouvelle visite sur la catégorie : {category.name}",
                recipients=[os.getenv('MAIL_USERNAME')],
                html=f"""
                <h2>Nouvelle visite sur votre catégorie</h2>
                <p>Une nouvelle personne a visité la catégorie : {category.name}</p>
                <ul>
                    <li>Date et heure : {page_view.viewed_at}</li>
                    <li>Navigateur : {request.user_agent.browser}</li>
                    <li>Plateforme : {request.user_agent.platform}</li>
                    <li>Provenance : {request.referrer or 'Accès direct'}</li>
                </ul>
                <p><a href="{url_for('category', slug=category.slug, _external=True)}">Voir la catégorie</a></p>
                """
            )
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    return render_template('category.html', articles=articles, category=category, categories=categories)

@app.route('/article/<slug>')
def article(slug):
    # Récupérer l'article avec toutes ses relations
    article_query = db_session.query(
        Article,
        Category.name.label('category_name'),
        Category.slug.label('category_slug'),
        Category.color_theme,
        User.username.label('author_name'),
        func.to_char(Article.created_at, 'DD/MM/YYYY').label('created_at_formatted')
    ).join(
        Category, Article.category_id == Category.id, isouter=True
    ).join(
        User, Article.author_id == User.id, isouter=True
    ).filter(Article.slug == slug).first()

    if article_query is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('index'))

    # Transformer l'article en dictionnaire
    article_dict = {
        'id': article_query.Article.id,
        'title': article_query.Article.title,
        'slug': article_query.Article.slug,
        'content': article_query.Article.content,
        'image_path': article_query.Article.image_path,
        'created_at': article_query.Article.created_at,
        'created_at_formatted': article_query.created_at_formatted,
        'category_name': article_query.category_name,
        'category_slug': article_query.category_slug,
        'color_theme': article_query.color_theme,
        'author_name': article_query.author_name
    }

    # Récupérer les commentaires avec les informations de l'auteur
    comments_query = db_session.query(
        Comment,
        User.username.label('author_name'),
        func.to_char(Comment.created_at, 'DD/MM/YYYY').label('created_at_formatted')
    ).join(
        User, Comment.user_id == User.id
    ).filter(
        Comment.article_id == article_dict['id']
    ).order_by(Comment.created_at.desc()).all()

    # Transformer les commentaires en dictionnaires
    comments = []
    for comment_row in comments_query:
        comment_dict = {
            'id': comment_row.Comment.id,
            'content': comment_row.Comment.content,
            'created_at': comment_row.Comment.created_at,
            'created_at_formatted': comment_row.created_at_formatted,
            'author_name': comment_row.author_name
        }
        comments.append(comment_dict)

    # Enregistrer la visite
    page_view = PageView(
        page='article',
        page_id=article_dict['id'],
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        is_bot=1 if request.user_agent.browser is None else 0,
        viewed_at=datetime.now()
    )
    db_session.add(page_view)
    db_session.commit()

    return render_template('article.html', article=article_dict, comments=comments)

# Routes d'administration
@app.route('/admin')
@login_required
@admin_required
def admin():
    # Récupérer les articles récents avec leurs relations
    articles_query = db_session.query(
        Article,
        Category.name.label('category_name'),
        Category.color_theme,
        User.username.label('author_name')
    ).join(
        Category, Article.category_id == Category.id, isouter=True
    ).join(
        User, Article.author_id == User.id, isouter=True
    ).order_by(Article.created_at.desc())

    # Transformer les résultats en dictionnaires
    articles = []
    for article_row in articles_query.all():
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'created_at': article_row.Article.created_at,
            'created_at_formatted': article_row.Article.created_at.strftime('%d/%m/%Y'),
            'category_name': article_row.category_name,
            'color_theme': article_row.color_theme,
            'author_name': article_row.author_name,
            'slug': article_row.Article.slug
        }
        articles.append(article_dict)
    
    # Récupérer les catégories
    categories = db_session.query(Category).all()
    
    # Récupérer les commentaires récents avec leurs relations
    comments_query = db_session.query(
        Comment,
        Article.title.label('article_title'),
        User.username.label('author_name')
    ).join(
        Article, Comment.article_id == Article.id, isouter=True
    ).join(
        User, Comment.user_id == User.id, isouter=True
    ).order_by(Comment.created_at.desc())

    # Transformer les résultats en dictionnaires
    comments = []
    for comment_row in comments_query.all():
        comment_dict = {
            'id': comment_row.Comment.id,
            'content': comment_row.Comment.content,
            'created_at': comment_row.Comment.created_at,
            'created_at_formatted': comment_row.Comment.created_at.strftime('%d/%m/%Y'),
            'article_title': comment_row.article_title,
            'author_name': comment_row.author_name
        }
        comments.append(comment_dict)
    
    return render_template('admin/dashboard.html',
                         articles=articles,
                         categories=categories,
                         comments=comments)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Récupérer les articles récents avec leurs relations
    articles_query = db_session.query(
        Article,
        Category.name.label('category_name'),
        Category.color_theme,
        User.username.label('author_name')
    ).join(
        Category, Article.category_id == Category.id, isouter=True
    ).join(
        User, Article.author_id == User.id, isouter=True
    ).order_by(Article.created_at.desc())

    # Transformer les résultats en dictionnaires
    articles = []
    for article_row in articles_query.all():
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'created_at': article_row.Article.created_at,
            'created_at_formatted': article_row.Article.created_at.strftime('%d/%m/%Y'),
            'category_name': article_row.category_name,
            'color_theme': article_row.color_theme,
            'author_name': article_row.author_name,
            'slug': article_row.Article.slug
        }
        articles.append(article_dict)
    
    # Récupérer les catégories
    categories = db_session.query(Category).all()
    
    # Récupérer les commentaires récents avec leurs relations
    comments_query = db_session.query(
        Comment,
        Article.title.label('article_title'),
        User.username.label('author_name'),
        func.to_char(Comment.created_at, 'DD/MM/YYYY').label('created_at_formatted')
    ).join(
        Article, Comment.article_id == Article.id
    ).join(
        User, Comment.user_id == User.id
    ).order_by(
        Comment.created_at.desc()
    ).limit(10)

    # Transformer les résultats en dictionnaires
    comments = []
    for comment_row in comments_query.all():
        comment_dict = {
            'id': comment_row.Comment.id,
            'content': comment_row.Comment.content,
            'created_at': comment_row.Comment.created_at,
            'created_at_formatted': comment_row.created_at_formatted,
            'article_title': comment_row.article_title,
            'author_name': comment_row.author_name
        }
        comments.append(comment_dict)
    
    # Statistiques
    total_articles = db_session.query(Article).count()
    total_comments = db_session.query(Comment).count()
    total_users = db_session.query(User).count()
    
    # Statistiques des visites
    today = datetime.utcnow().date()
    today_views = db_session.query(PageView).filter(
        func.date(PageView.viewed_at) == today
    ).count()
    
    # Statistiques des abonnés
    total_subscribers = db_session.query(NewsletterSubscriber).count()
    active_subscribers = db_session.query(NewsletterSubscriber).filter_by(status='active').count()
    
    # Dernières newsletters envoyées
    recent_newsletters = db_session.query(NewsletterHistory).order_by(
        NewsletterHistory.sent_at.desc()
    ).limit(5).all()
    
    # Articles les plus vus cette semaine
    week_start = today - timedelta(days=today.weekday())
    top_articles_query = db_session.query(
        Article,
        func.count(PageView.id).label('views')
    ).outerjoin(
        PageView,
        and_(
            PageView.page == 'article',
            PageView.page_id == Article.id,
            func.date(PageView.viewed_at) >= week_start
        )
    ).group_by(Article.id).order_by(
        desc('views')
    ).limit(5)

    # Transformer les résultats en dictionnaires
    top_articles = []
    for article_row in top_articles_query.all():
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'views': article_row.views,
            'slug': article_row.Article.slug
        }
        top_articles.append(article_dict)
    
    return render_template('admin/dashboard.html',
                         articles=articles,
                         categories=categories,
                         comments=comments,
                         total_articles=total_articles,
                         total_comments=total_comments,
                         total_users=total_users,
                         today_views=today_views,
                         total_subscribers=total_subscribers,
                         active_subscribers=active_subscribers,
                         recent_newsletters=recent_newsletters,
                         top_articles=top_articles)

class ArticleForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    category = SelectField('Catégorie', coerce=int, validators=[DataRequired()])
    images = FileField('Images', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    tags = StringField('Tags')
    
    def __init__(self, *args, **kwargs):
        super(ArticleForm, self).__init__(*args, **kwargs)
        self.category.choices = [(c['id'], c['name']) for c in get_all_categories()]

@app.route('/admin/articles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_article():
    form = ArticleForm()
    
    if form.validate_on_submit():
        try:
            title = form.title.data
            content = form.content.data
            category_id = form.category.data
            
            # Gestion des images
            image_paths = []
            if request.files.getlist('images'):
                for file in request.files.getlist('images'):
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        rel_path = os.path.join('uploads', filename).replace('\\', '/')
                        image_paths.append(rel_path)
            
            slug = slugify(title)
            image_path = ','.join(image_paths) if image_paths else None
            
            article = Article(
                title=title,
                slug=slug,
                content=content,
                category_id=category_id,
                author_id=current_user.id,
                image_path=image_path
            )
            db_session.add(article)
            db_session.commit()
            
            flash('Article créé avec succès !', 'success')
            return redirect(url_for('manage_articles'))
        except Exception as e:
            db_session.rollback()
            flash('Erreur lors de la création de l\'article.', 'error')
            print(f"Erreur lors de la création de l'article : {e}")
    
    return render_template('admin/article_form.html', form=form)

# Route pour la newsletter
@app.route('/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if email:
        subscriber = db_session.query(NewsletterSubscriber).filter_by(email=email).first()
        if not subscriber:
            subscriber = NewsletterSubscriber(
                email=email,
                status='pending',
                subscribed_at=datetime.now()
            )
            db_session.add(subscriber)
            db_session.commit()
            flash('Inscription à la newsletter réussie !', 'success')
        else:
            flash('Vous êtes déjà inscrit à la newsletter.', 'info')
    return redirect(url_for('index'))

# Routes pour la gestion de la newsletter
@app.route('/admin/newsletter')
@login_required
@admin_required
def manage_newsletter():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    total_subscribers = db_session.query(NewsletterSubscriber).count()
    subscribers = db_session.query(NewsletterSubscriber).order_by(NewsletterSubscriber.subscribed_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    recent_articles = db_session.query(Article).order_by(Article.created_at.desc()).limit(5).all()
    newsletter_history = db_session.query(NewsletterHistory).order_by(NewsletterHistory.sent_at.desc()).limit(10).all()

    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total_subscribers + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total_subscribers,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': subscribers
    })
    
    return render_template('admin/manage_newsletter.html', 
                         subscribers=pagination,
                         recent_articles=recent_articles,
                         newsletter_history=newsletter_history)

@app.route('/admin/newsletter/send', methods=['POST'])
@login_required
@admin_required
def send_newsletter():
    data = request.get_json()
    subject = data.get('subject')
    content = data.get('content')
    article_ids = data.get('articles', [])
    test_send = data.get('test_send', False)
    recipient_type = data.get('recipient_type', 'all')
    selected_subscribers = data.get('subscribers', [])
    admin_email = os.environ.get('MAIL_USERNAME')

    if not subject or not content:
        return jsonify({'success': False, 'message': 'Le sujet et le contenu sont requis'})

    try:
        articles = []
        if article_ids:
            articles = db_session.query(Article).filter(Article.id.in_(article_ids)).all()
        html_content = content
        if articles:
            html_content += '<h2>Articles récents</h2>'
            for article in articles:
                excerpt = article.content[:200] + '...' if len(article.content) > 200 else article.content
                html_content += f'''
                <div style="margin-bottom: 20px;">
                    <h3>{article.title}</h3>
                    <p>{excerpt}</p>
                    <a href="{url_for('article', slug=article.slug, _external=True)}">Lire la suite</a>
                </div>
                '''
        recipient_count = 0
        if test_send:
            if not admin_email:
                return jsonify({'success': False, 'message': 'Email administrateur non configuré'})
            msg = Message(
                subject=f"[TEST] {subject}",
                recipients=[admin_email],
                html=html_content
            )
            mail.send(msg)
            recipient_count = 1
            message = 'Email de test envoyé à l\'administrateur'
        else:
            if recipient_type == 'all':
                subscribers = db_session.query(NewsletterSubscriber).filter_by(status='active').all()
            else:
                if not selected_subscribers:
                    return jsonify({'success': False, 'message': 'Aucun destinataire sélectionné'})
                subscribers = db_session.query(NewsletterSubscriber).filter(NewsletterSubscriber.id.in_(selected_subscribers), NewsletterSubscriber.status=='active').all()
            if not subscribers:
                if not admin_email:
                    return jsonify({'success': False, 'message': 'Aucun destinataire actif trouvé et email administrateur non configuré'})
                msg = Message(
                    subject=subject,
                    recipients=[admin_email],
                    html=html_content + '<p><em>Note: Cette newsletter a été envoyée uniquement à l\'administrateur car aucun abonné actif n\'a été trouvé.</em></p>'
                )
                mail.send(msg)
                recipient_count = 1
                message = 'Newsletter envoyée uniquement à l\'administrateur (aucun abonné actif)'
            else:
                success_count = 0
                error_count = 0
            for subscriber in subscribers:
                try:
                    msg = Message(
                        subject=subject,
                            recipients=[subscriber.email],
                        html=html_content
                    )
                    mail.send(msg)
                    subscriber.last_newsletter = datetime.now()
                    db_session.commit()
                    success_count += 1
                except Exception as e:
                    print(f"Erreur lors de l'envoi à {subscriber.email}: {str(e)}")
                    error_count += 1
                    continue
                recipient_count = success_count
                message = f'Newsletter envoyée à {success_count} destinataire(s)'
                if error_count > 0:
                    message += f' ({error_count} échec(s))'
        nh = NewsletterHistory(
            subject=subject,
            content=html_content,
            sent_by=current_user.id,
            recipient_count=recipient_count,
            test_send=test_send
        )
        db_session.add(nh)
        db_session.commit()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        print(f"Erreur lors de l'envoi de la newsletter: {str(e)}")
        db_session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/newsletter/<int:newsletter_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_newsletter(newsletter_id):
    newsletter = db_session.query(NewsletterHistory).filter_by(id=newsletter_id).first_or_404()
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        article_ids = request.form.getlist('articles')
        
        if not subject or not content:
            flash('Le sujet et le contenu sont requis.', 'error')
            return redirect(url_for('edit_newsletter', newsletter_id=newsletter_id))
        
        try:
            newsletter.subject = subject
            newsletter.content = content
            newsletter.article_ids = ','.join(map(str, article_ids))
            newsletter.updated_at = datetime.now()
            db_session.commit()
            
            flash('Newsletter modifiée avec succès !', 'success')
            return redirect(url_for('manage_newsletter'))
        except Exception as e:
            db_session.rollback()
            flash('Erreur lors de la modification de la newsletter.', 'error')
            print(f"Erreur lors de la modification de la newsletter : {e}")
            return redirect(url_for('edit_newsletter', newsletter_id=newsletter_id))
    
    # Récupérer tous les articles pour le formulaire
    articles = db_session.query(Article).order_by(Article.created_at.desc()).all()
    
    # Convertir les IDs d'articles en liste
    selected_articles = newsletter.article_ids.split(',') if newsletter.article_ids else []
    
    return render_template('admin/edit_newsletter.html', 
                         newsletter=newsletter, 
                         articles=articles,
                         selected_articles=selected_articles)

@app.route('/admin/newsletter/<int:newsletter_id>/content')
@login_required
@admin_required
def get_newsletter_content(newsletter_id):
    try:
        newsletter = db_session.query(NewsletterHistory).filter_by(id=newsletter_id).first()
        
        if newsletter:
            return jsonify({
                'success': True,
                'content': newsletter.content
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Newsletter non trouvée'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Mise à jour des fonctions utilitaires pour les newsletters
def get_all_newsletters():
    return db_session.query(NewsletterHistory).order_by(NewsletterHistory.sent_at.desc()).all()

def get_newsletter_by_id(newsletter_id):
    return db_session.query(NewsletterHistory).filter_by(id=newsletter_id).first()

def create_newsletter(subject, content, sent_by, recipient_count=0, test_send=False):
    newsletter = NewsletterHistory(
        subject=subject,
        content=content,
        sent_by=sent_by,
        recipient_count=recipient_count,
        test_send=test_send,
        sent_at=datetime.now()
    )
    db_session.add(newsletter)
    db_session.commit()
    return newsletter

def update_newsletter(newsletter_id, subject, content, article_ids=None):
    newsletter = db_session.query(NewsletterHistory).filter_by(id=newsletter_id).first()
    if newsletter:
        newsletter.subject = subject
        newsletter.content = content
        if article_ids is not None:
            newsletter.article_ids = ','.join(map(str, article_ids))
        newsletter.updated_at = datetime.now()
        db_session.commit()
        return True
    return False

def delete_newsletter(newsletter_id):
    newsletter = db_session.query(NewsletterHistory).filter_by(id=newsletter_id).first()
    if newsletter:
        db_session.delete(newsletter)
        db_session.commit()
        return True
    return False

# Mise à jour de la route d'import des abonnés
@app.route('/admin/newsletter/import', methods=['POST'])
@login_required
@admin_required
def import_subscribers():
    if 'importFile' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier n\'a été envoyé'})

    file = request.files['importFile']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'})

    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Le fichier doit être au format CSV'})

    try:
        # Lire le fichier CSV
        stream = TextIOWrapper(file.stream, encoding='utf-8')
        csv_reader = csv.DictReader(stream)
        
        count = 0
        for row in csv_reader:
            if 'email' in row and row['email']:
                # Vérifier si l'email existe déjà
                existing = db_session.query(NewsletterSubscriber).filter_by(email=row['email']).first()
                if not existing:
                    subscriber = NewsletterSubscriber(
                        email=row['email'],
                        status='active',
                        subscribed_at=datetime.now()
                    )
                    db_session.add(subscriber)
                    count += 1

        db_session.commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Mise à jour de la route d'export des abonnés
@app.route('/admin/newsletter/export')
@login_required
@admin_required
def export_subscribers():
    try:
        # Créer un fichier CSV en mémoire
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['email', 'status', 'subscribed_at', 'last_newsletter'])

        subscribers = db_session.query(NewsletterSubscriber).all()
        for subscriber in subscribers:
            writer.writerow([
                subscriber.email,
                subscriber.status,
                subscriber.subscribed_at.strftime('%Y-%m-%d %H:%M:%S'),
                subscriber.last_newsletter.strftime('%Y-%m-%d %H:%M:%S') if subscriber.last_newsletter else ''
            ])

        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=subscribers.csv'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/newsletter/subscribers/<int:subscriber_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subscriber(subscriber_id):
    subscriber = db_session.query(NewsletterSubscriber).filter_by(id=subscriber_id).first()
    if not subscriber:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    try:
        db_session.delete(subscriber)
        db_session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/newsletter/subscribers/<int:subscriber_id>/<action>', methods=['POST'])
@login_required
@admin_required
def toggle_subscriber_status(subscriber_id, action):
    if action not in ['unsubscribe', 'resubscribe']:
        return jsonify({'success': False, 'message': 'Action invalide'})
    subscriber = db_session.query(NewsletterSubscriber).filter_by(id=subscriber_id).first()
    if not subscriber:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    try:
        if action == 'unsubscribe':
            subscriber.status = 'unsubscribed'
        else:
            subscriber.status = 'active'
        db_session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'message': str(e)})

def generate_session_code():
    return ''.join(random.choices(string.digits, k=6))

def send_admin_verification_email(user_email, session_code):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = user_email
        msg['Subject'] = "Code de vérification administrateur - PowerDataLab"

        # S'assurer que le code est une chaîne de caractères
        session_code = str(session_code).strip()
        print(f"Tentative d'envoi du code: {session_code} à {user_email}")

        body = f"""
        Bonjour,

        Voici votre code de vérification pour la session administrateur : {session_code}

        Ce code est valable pendant 15 minutes.

        Cordialement,
        L'équipe PowerDataLab
        """
        msg.attach(MIMEText(body, 'plain'))

        # Configuration du serveur SMTP
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.set_debuglevel(1)  # Activer le mode debug pour voir les détails de la connexion
        server.starttls()
        
        # Vérifier que les identifiants sont présents
        if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
            print("Erreur: Identifiants SMTP manquants")
            print(f"MAIL_USERNAME: {'Présent' if app.config['MAIL_USERNAME'] else 'Manquant'}")
            print(f"MAIL_PASSWORD: {'Présent' if app.config['MAIL_PASSWORD'] else 'Manquant'}")
            return False

        # Connexion au serveur
        print(f"Tentative de connexion à {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        
        # Envoi de l'email
        print("Envoi de l'email...")
        server.send_message(msg)
        server.quit()
        print("Email envoyé avec succès")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Erreur d'authentification SMTP: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"Erreur SMTP: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue lors de l'envoi d'email: {e}")
        return False

class AdminVerifyForm(FlaskForm):
    code = StringField('Code de vérification', validators=[DataRequired()])

@app.route('/admin/verify', methods=['GET'])
def admin_verify():
    if not session.get('admin_email'):
        return redirect(url_for('login'))
    form = AdminVerifyForm()
    return render_template('admin_verify.html', form=form)

@app.route('/admin/verify-code', methods=['POST'])
def verify_admin_code():
    if not session.get('admin_email'):
        return redirect(url_for('login'))
    
    form = AdminVerifyForm()
    if form.validate_on_submit():
        code = form.code.data
    stored_code = session.get('admin_code')
    expiry_time = session.get('admin_code_expiry')
    
    if stored_code and expiry_time and isinstance(expiry_time, datetime):
        current_time = datetime.now().replace(tzinfo=None)
        expiry_time = expiry_time.replace(tzinfo=None)
        
        if current_time < expiry_time:
            if code == stored_code:
                # Vérifier si l'utilisateur admin existe déjà
                    user = db_session.query(User).filter_by(email=session['admin_email']).first()
                
                    if user:
                        # L'utilisateur existe déjà, on le connecte
                        login_user(user)
                    else:
                        # Créer un nouvel utilisateur admin
                            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                            user = User(
                                username='admin',
                                email=session['admin_email'],
                                password_hash=generate_password_hash(password),
                                is_admin=True,
                                is_blocked=False
                            )
                            db_session.add(user)
                            db_session.commit()
                    login_user(user)
                        
                    session.pop('admin_code', None)
                    session.pop('admin_code_expiry', None)
                    session.pop('admin_email', None)
                    flash('Vérification réussie !', 'success')
                    return redirect(url_for('admin_dashboard'))
            else:
                flash('Code invalide', 'error')
        else:
            flash('Code expiré', 'error')
            # Générer un nouveau code
            session_code = generate_session_code()
            session['admin_code'] = session_code
            session['admin_code_expiry'] = datetime.now().replace(tzinfo=None) + timedelta(minutes=15)
            
            if send_admin_verification_email(session['admin_email'], session_code):
                flash('Un nouveau code a été envoyé à votre email', 'info')
            else:
                flash('Erreur lors de l\'envoi du code. Veuillez réessayer.', 'error')
    else:
        flash('Session invalide ou expirée', 'error')
    
    return redirect(url_for('admin_verify'))

@app.before_request
def load_categories():
    if 'categories' not in g:
        # Récupérer les catégories avec leur nombre d'articles
        categories = db_session.query(
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

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=lambda: csrf._get_csrf_token())

class CSRFProtectForm(FlaskForm):
    pass

@app.route('/admin/articles')
@login_required
@admin_required
def manage_articles():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Calculer le nombre total d'articles
    total = db_session.query(Article).count()
    
    # Calculer l'offset pour la pagination
    offset = (page - 1) * per_page

    # Récupérer les articles avec leurs catégories
    articles_query = db_session.query(
        Article,
        Category.name.label('category_name'),
        Category.color_theme
    ).join(
        Category, Article.category_id == Category.id, isouter=True
    ).order_by(Article.created_at.desc()).offset(offset).limit(per_page)

    # Transformer les résultats en dictionnaires pour faciliter l'accès dans le template
    articles = []
    for article_row in articles_query.all():
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'created_at': article_row.Article.created_at,
            'created_at_formatted': article_row.Article.created_at.strftime('%d/%m/%Y'),
            'category_name': article_row.category_name,
            'color_theme': article_row.color_theme
        }
        articles.append(article_dict)
    
    # Créer un objet de pagination personnalisé
    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': articles
    })
    
    form = FlaskForm()  # Créer un formulaire vide pour le token CSRF
    return render_template('admin/manage_articles.html', articles=pagination, form=form)

def clean_duplicate_images():
    """Nettoie les images en double dans le dossier uploads."""
    print("Début du nettoyage des images...")
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        print(f"Dossier uploads non trouvé: {upload_dir}")
        return

    # Dictionnaire pour stocker les fichiers par nom final
    files_by_name = {}
    
    # Parcourir tous les fichiers dans le dossier uploads
    for filename in os.listdir(upload_dir):
        if not os.path.isfile(os.path.join(upload_dir, filename)):
            continue
            
        # Extraire le nom final en ignorant le timestamp
        parts = filename.split('_')
        if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:  # Format timestamp
            base_name = '_'.join(parts[2:])
        else:
            base_name = filename
            
        file_path = os.path.join(upload_dir, filename)
        mod_time = os.path.getmtime(file_path)
        print(f"Traitement du fichier: {filename}")
        print(f"  - Nom de base: {base_name}")
        print(f"  - Date de modification: {datetime.fromtimestamp(mod_time)}")
        
        if base_name in files_by_name:
            old_path, old_time = files_by_name[base_name]
            print(f"Doublon trouvé!")
            print(f"  - Ancien fichier: {os.path.basename(old_path)} (modifié: {datetime.fromtimestamp(old_time)})")
            print(f"  - Nouveau fichier: {filename} (modifié: {datetime.fromtimestamp(mod_time)})")
            
            if mod_time > old_time:
                print(f"  → Suppression de l'ancien fichier: {os.path.basename(old_path)}")
                try:
                    os.remove(old_path)
                    files_by_name[base_name] = (file_path, mod_time)
                except Exception as e:
                    print(f"  → Erreur lors de la suppression: {e}")
            else:
                print(f"  → Suppression du nouveau fichier: {filename}")
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"  → Erreur lors de la suppression: {e}")
        else:
            files_by_name[base_name] = (file_path, mod_time)
            print(f"  → Nouveau fichier unique")
    
    print("\nMise à jour de la base de données...")
    # Mettre à jour les chemins dans la base de données
    articles = db_session.query(Article).filter(Article.image_path.isnot(None)).all()
    
    for article in articles:
        if not article.image_path:
            continue
            
        # Séparer les chemins d'images
        image_paths = article.image_path.split(',')
        valid_paths = []
        
        for path in image_paths:
            path = path.strip()
            if not path:
                continue
                
            # Vérifier si le fichier existe toujours
            filename = os.path.basename(path)
            if os.path.exists(os.path.join(upload_dir, filename)):
                valid_paths.append(path)
            else:
                print(f"Image non trouvée dans la base de données: {filename}")
        
        # Mettre à jour l'article avec les chemins valides
        if valid_paths:
            article.image_path = ','.join(valid_paths)
            print(f"Article {article.id} mis à jour avec {len(valid_paths)} images valides")
        else:
            article.image_path = None
            print(f"Article {article.id} mis à jour: aucune image valide")
    
    try:
        db_session.commit()
        print("\nNettoyage terminé.")
    except Exception as e:
        db_session.rollback()
        print(f"\nErreur lors de la mise à jour de la base de données: {e}")

@app.route('/admin/articles/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_article():
    if request.method == 'POST':
        try:
            title = request.form['title']
            content = request.form['content']
            category_id = request.form['category_id']
            slug = slugify(title)
            
            # Gestion des images multiples
            image_paths = []
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        rel_path = os.path.join('uploads', filename).replace('\\', '/')
                        image_paths.append(rel_path)
            
            # Nettoyer la liste (supprimer les vides)
            image_paths = [p for p in image_paths if p]
            image_path = ','.join(image_paths) if image_paths else None
            
            article = Article(
                title=title,
                slug=slug,
                content=content,
                category_id=category_id,
                author_id=current_user.id,
                image_path=image_path
            )
            db_session.add(article)
            db_session.commit()
            
            # Nettoyer les images en double
            clean_duplicate_images()
            
            flash('Article créé avec succès !', 'success')
            return redirect(url_for('manage_articles'))
        except Exception as e:
            db_session.rollback()
            flash('Erreur lors de la création de l\'article.', 'error')
            print(f"Erreur lors de la création de l'article : {e}")
    
    categories = db_session.query(Category).order_by(Category.name).all()
    return render_template('admin/article_form.html', categories=categories)

@app.route('/admin/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_article(article_id):
    article = db_session.query(Article).filter_by(id=article_id).first()
    
    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']
        article.category_id = request.form['category_id']
        article.slug = slugify(article.title)
        
        # Gestion des images existantes et nouvelles
        existing_images = request.form.getlist('existing_images')
        image_paths = [img.replace('\\', '/') for img in existing_images if img]
        
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        rel_path = os.path.join('uploads', filename).replace('\\', '/')
                        image_paths.append(rel_path)
        
        # Nettoyer la liste (supprimer les vides)
        image_paths = [p for p in image_paths if p]
        article.image_path = ','.join(image_paths) if image_paths else None
        article.updated_at = datetime.now()
        
        db_session.commit()
        
        # Nettoyer les images en double
        clean_duplicate_images()
        
        flash('Article modifié avec succès !', 'success')
        return redirect(url_for('manage_articles'))
    
    categories = db_session.query(Category).order_by(Category.name).all()
    return render_template('admin/article_form.html', article=article, categories=categories)

@app.route('/admin/articles/delete/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def delete_article_route(article_id):
    article = db_session.query(Article).filter_by(id=article_id).first()
    if article is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('manage_articles'))
    
    try:
        # Supprimer l'image si elle existe
        if article.image_path:
            try:
                for image_path in article.image_path.split(','):
                    full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))
                    if os.path.exists(full_path):
                        os.remove(full_path)
            except Exception as e:
                print(f"Erreur lors de la suppression de l'image : {e}")
        
        # Supprimer l'article
        db_session.delete(article)
        db_session.commit()
        
        flash('Article supprimé avec succès!', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la suppression de l\'article.', 'error')
        print(f"Erreur lors de la suppression de l'article : {e}")
    
    return redirect(url_for('manage_articles'))

@app.route('/admin/comments')
@login_required
@admin_required
def manage_comments():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    total = db_session.query(Comment).count()
    
    # Récupérer les commentaires avec leurs relations
    comments_query = db_session.query(
        Comment,
        User.username.label('author_name'),
        Article.title.label('article_title'),
        func.to_char(Comment.created_at, 'DD/MM/YYYY').label('created_at_formatted')
    ).join(
        User, Comment.user_id == User.id
    ).join(
        Article, Comment.article_id == Article.id
    ).order_by(Comment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Transformer les résultats en dictionnaires
    comments = []
    for comment_row in comments_query:
        comment_dict = {
            'id': comment_row.Comment.id,
            'content': comment_row.Comment.content,
            'created_at': comment_row.Comment.created_at,
            'created_at_formatted': comment_row.created_at_formatted,
            'author_name': comment_row.author_name,
            'article_title': comment_row.article_title,
            'is_approved': comment_row.Comment.is_approved if hasattr(comment_row.Comment, 'is_approved') else True
        }
        comments.append(comment_dict)
    
    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': comments
    })
    return render_template('admin/manage_comments.html', comments=pagination)

@app.route('/admin/comments/delete/<int:comment_id>', methods=['POST'])
@login_required
@admin_required
def delete_comment_route(comment_id):
    comment = db_session.query(Comment).filter_by(id=comment_id).first()
    if comment is None:
        flash('Commentaire non trouvé.', 'error')
        return redirect(url_for('manage_comments'))
    try:
        db_session.delete(comment)
        db_session.commit()
        flash('Commentaire supprimé avec succès!', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la suppression du commentaire.', 'error')
        print(f"Erreur lors de la suppression du commentaire : {e}")
    return redirect(url_for('manage_comments'))

@app.route('/article/<slug>/comment', methods=['POST'])
@login_required
def add_comment(slug):
    article = db_session.query(Article).filter_by(slug=slug).first()
    if article is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('index'))
    content = request.form.get('content')
    if not content:
        flash('Le contenu du commentaire est requis.', 'error')
        return redirect(url_for('article', slug=slug))
    comment = Comment(
        content=content,
        article_id=article.id,
        user_id=current_user.id
    )
    db_session.add(comment)
    db_session.commit()
    flash('Commentaire ajouté avec succès!', 'success')
    return redirect(url_for('article', slug=slug))

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Compter le nombre total d'utilisateurs
    total = db_session.query(User).count()
    
    # Récupérer les utilisateurs avec pagination et leurs statistiques
    users_query = db_session.query(
        User,
        func.count(Article.id).label('article_count'),
        func.count(Comment.id).label('comment_count')
    ).outerjoin(
        Article, User.id == Article.author_id
    ).outerjoin(
        Comment, User.id == Comment.user_id
    ).group_by(User.id).order_by(
        User.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()
    
    # Transformer les résultats en dictionnaires
    users = []
    for user_row in users_query:
        user_dict = {
            'id': user_row.User.id,
            'username': user_row.User.username,
            'email': user_row.User.email,
            'is_admin': user_row.User.is_admin,
            'is_blocked': user_row.User.is_blocked,
            'created_at': user_row.User.created_at,
            'created_at_formatted': user_row.User.created_at.strftime('%d/%m/%Y'),
            'article_count': user_row.article_count,
            'comment_count': user_row.comment_count
        }
        users.append(user_dict)
    
    # Créer l'objet de pagination
    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': users
    })
    
    return render_template('admin/manage_users.html', users=pagination)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'error')
        return redirect(url_for('manage_users'))
    
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        flash('Utilisateur non trouvé.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        # Supprimer d'abord les articles et commentaires de l'utilisateur
        db_session.query(Article).filter_by(author_id=user_id).delete()
        db_session.query(Comment).filter_by(user_id=user_id).delete()  # Correction ici : user_id au lieu de author_id
        
        # Puis supprimer l'utilisateur
        db_session.delete(user)
        db_session.commit()
        flash('Utilisateur supprimé avec succès !', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la suppression de l\'utilisateur.', 'error')
        print(f"Erreur lors de la suppression de l'utilisateur : {e}")
    
    return redirect(url_for('manage_users'))

@app.route('/admin/update-categories')
@login_required
@admin_required
def update_categories():
    try:
    # Supprimer toutes les catégories existantes
        db_session.query(Category).delete()
    
        # Définir les nouvelles catégories
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
            'power-virtual-agents': {
                'name': 'Power Virtual Agents',
                'color': '#00B7C3',
                'description': 'Création de chatbots avec Power Virtual Agents'
            },
            'sharepoint': {
                'name': 'SharePoint',
                'color': '#217346',
                'description': 'Gestion de contenu et collaboration avec SharePoint'
            },
            'divers': {
                'name': 'Divers',
                'color': '#6c757d',
                'description': 'Articles divers et variés'
            }
        }
    
        # Créer les nouvelles catégories
        for slug, data in categories.items():
            category = Category(
                name=data['name'],
                slug=slug,
                color_theme=data['color'],
                description=data['description']
            )
            db_session.add(category)
            
            db_session.commit()
            flash('Catégories mises à jour avec succès !', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la mise à jour des catégories.', 'error')
        print(f"Erreur: {e}")
    
    return redirect(url_for('admin'))

@app.route('/admin/categories')
@login_required
@admin_required
def manage_categories():
    categories = db_session.query(Category).all()
    return render_template('admin/manage_categories.html', categories=categories)

@app.route('/admin/categories/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_category():
    print("\n=== Début de la requête new_category ===")
    print(f"Méthode: {request.method}")
    
    if request.method == 'POST':
        print("\n=== Traitement POST ===")
        try:
            # Flask-WTF vérifie automatiquement le token CSRF
            name = request.form.get('name')
            color_theme = request.form.get('color_theme')
            description = request.form.get('description')
            
            print(f"\nDonnées reçues:")
            print(f"Nom: {name}")
            print(f"Couleur: {color_theme}")
            print(f"Description: {description}")
            
            if not name or not color_theme:
                flash('Le nom et la couleur sont requis', 'error')
                return redirect(url_for('manage_categories'))
            
            try:
                slug = slugify(name)
                category = Category(
                    name=name,
                    slug=slug,
                    color_theme=color_theme,
                    description=description
                )
                db_session.add(category)
                db_session.commit()
                
                flash('Catégorie créée avec succès', 'success')
                return redirect(url_for('manage_categories'))
            except Exception as e:
                db_session.rollback()
                print(f"Erreur lors de la création: {str(e)}")
                flash('Erreur lors de la création de la catégorie', 'error')
                return redirect(url_for('manage_categories'))
                
        except Exception as e:
            print(f"Erreur lors du traitement POST: {str(e)}")
            flash('Erreur lors de la création de la catégorie', 'error')
            return redirect(url_for('manage_categories'))
    
    # Pour les requêtes GET, on affiche simplement le formulaire
    return render_template('admin/manage_categories.html')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    print("\n=== Début de la requête edit_category ===")
    print(f"Méthode: {request.method}")
    print(f"ID catégorie: {category_id}")
    
    if request.method == 'POST':
        print("\n=== Traitement POST ===")
        try:
            # Flask-WTF vérifie automatiquement le token CSRF
            name = request.form.get('name')
            color_theme = request.form.get('color_theme')
            description = request.form.get('description')
            
            print(f"\nDonnées reçues:")
            print(f"Nom: {name}")
            print(f"Couleur: {color_theme}")
            print(f"Description: {description}")
            
            if not name or not color_theme:
                flash('Le nom et la couleur sont requis', 'error')
                return redirect(url_for('manage_categories'))
            
            category = db_session.query(Category).filter_by(id=category_id).first()
            if category is None:
                flash('Catégorie non trouvée', 'error')
                return redirect(url_for('manage_categories'))
            
            try:
                category.name = name
                category.slug = slugify(name)
                category.color_theme = color_theme
                category.description = description
                db_session.commit()
                
                flash('Catégorie mise à jour avec succès', 'success')
                return redirect(url_for('manage_categories'))
            except Exception as e:
                db_session.rollback()
                print(f"Erreur lors de la mise à jour: {str(e)}")
                flash('Erreur lors de la mise à jour de la catégorie', 'error')
                return redirect(url_for('manage_categories'))
                
        except Exception as e:
            db_session.rollback()
            print(f"Erreur lors de la mise à jour: {str(e)}")
            flash('Erreur lors de la mise à jour de la catégorie', 'error')
            return redirect(url_for('manage_categories'))
    
    # Pour les requêtes GET, on récupère la catégorie
    category = db_session.query(Category).get(category_id)
    if not category:
        flash('Catégorie non trouvée.', 'error')
        return redirect(url_for('manage_categories'))
    
    # Vérifier si la catégorie a des articles associés
    has_articles = db_session.query(Article).filter_by(category_id=category_id).first() is not None
    
    return render_template('admin/manage_categories.html', 
                         category=category, 
                         is_edit=True,
                         has_articles=has_articles)

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category_route(category_id):
    try:
        category = db_session.query(Category).get(category_id)
        if not category:
            flash('Catégorie non trouvée.', 'error')
            return redirect(url_for('manage_categories'))
        
        # Vérifier si la catégorie a des articles associés
        if category.articles:
            flash('Impossible de supprimer une catégorie qui contient des articles.', 'error')
            return redirect(url_for('manage_categories'))
        
        db_session.delete(category)
        db_session.commit()
        flash('Catégorie supprimée avec succès.', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'Erreur lors de la suppression de la catégorie: {str(e)}', 'error')
    
    return redirect(url_for('manage_categories'))

@app.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    # Statistiques générales
    total_views = db_session.query(PageView).count()
    unique_visitors = db_session.query(PageView.ip_address.distinct()).count()
    
    # Visites aujourd'hui
    today = datetime.utcnow().date()
    today_views = db_session.query(PageView).filter(
        func.date(PageView.viewed_at) == today
    ).count()
    
    # Visites cette semaine
    week_start = today - timedelta(days=today.weekday())
    week_views = db_session.query(PageView).filter(
        func.date(PageView.viewed_at) >= week_start,
        func.date(PageView.viewed_at) < today
    ).count()
    
    # Statistiques par page
    page_stats = db_session.query(
        PageView.page,
        func.count(PageView.id).label('views')
    ).group_by(PageView.page).all()
    
    # Statistiques des 7 derniers jours
    last_week = datetime.utcnow() - timedelta(days=7)
    daily_stats = db_session.query(
        func.date(PageView.viewed_at).label('date'),
        func.count(PageView.id).label('views')
    ).filter(
        PageView.viewed_at >= last_week,
        PageView.viewed_at < datetime.utcnow()
    ).group_by(
        func.date(PageView.viewed_at)
    ).all()
    
    # Statistiques des navigateurs
    browser_stats = db_session.query(
        func.substring(PageView.user_agent, 1, 50).label('browser'),
        func.count(PageView.id).label('count')
    ).group_by(
        func.substring(PageView.user_agent, 1, 50)
    ).all()
    
    # Statistiques des sources de trafic
    referrer_stats = db_session.query(
        func.coalesce(PageView.referrer, 'Direct').label('source'),
        func.count(PageView.id).label('count')
    ).group_by(
        func.coalesce(PageView.referrer, 'Direct')
    ).all()
    
    # Articles les plus vus
    top_articles = db_session.query(
        Article,
        func.count(PageView.id).label('views')
    ).outerjoin(
        PageView,
        and_(
            PageView.page == 'article',
            PageView.page_id == Article.id
        )
    ).group_by(Article.id).order_by(
        text('views DESC')
    ).limit(10).all()
    
    # Transformer les résultats en dictionnaires
    top_articles_list = []
    for article_row in top_articles:
        article_dict = {
            'id': article_row.Article.id,
            'title': article_row.Article.title,
            'slug': article_row.Article.slug,
            'views': article_row.views
        }
        top_articles_list.append(article_dict)
    
    # Catégories les plus vues
    top_categories = db_session.query(
        Category,
        func.count(PageView.id).label('views')
    ).outerjoin(
        PageView,
        and_(
            or_(
                and_(PageView.page == 'category', PageView.page_id == Category.id),
                and_(PageView.page == 'article', PageView.page_id.in_(
                    db_session.query(Article.id).filter(Article.category_id == Category.id)
                ))
            )
        )
    ).group_by(Category.id).order_by(
        text('views DESC')
    ).limit(10).all()
    
    # Transformer les résultats en dictionnaires
    top_categories_list = []
    for category_row in top_categories:
        category_dict = {
            'id': category_row.Category.id,
            'name': category_row.Category.name,
            'slug': category_row.Category.slug,
            'color_theme': category_row.Category.color_theme,
            'views': category_row.views
        }
        top_categories_list.append(category_dict)
    
    return render_template('admin/analytics.html',
                         total_views=total_views,
                         unique_visitors=unique_visitors,
                         today_views=today_views,
                         week_views=week_views,
                         page_stats=page_stats,
                         daily_stats=daily_stats,
                         browser_stats=browser_stats,
                         referrer_stats=referrer_stats,
                         top_articles=top_articles_list,
                         top_categories=top_categories_list)

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db_session.query(User).filter_by(email=form.email.data).first()
        
        if user:
            # Générer un token unique
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            
            # Sauvegarder le token dans la base de données
            user.reset_token = token
            user.reset_token_expiry = expiry
            db_session.commit()
            
            # Envoyer l'email
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message(
                'Réinitialisation de votre mot de passe',
                recipients=[form.email.data],
                html=render_template('email/reset_password.html', 
                                   reset_url=reset_url,
                                   username=user.username)
            )
            try:
                mail.send(msg)
                flash('Un email avec les instructions de réinitialisation a été envoyé.', 'info')
            except Exception as e:
                flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'error')
                print(f"Erreur d'envoi d'email: {e}")
        else:
            # Pour des raisons de sécurité, on affiche le même message même si l'email n'existe pas
            flash('Si votre email est enregistré, vous recevrez les instructions de réinitialisation.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('reset_password_request.html', form=form)

@app.route('/reset-db')
def reset_db():
    """Réinitialise la base de données (à utiliser uniquement en développement)"""
    if os.getenv('FLASK_ENV') == 'production':
        return "Cette action n'est pas autorisée en production", 403
    
    try:
        # Supprimer toutes les tables
        Base.metadata.drop_all(engine)
        # Recréer toutes les tables
        Base.metadata.create_all(engine)
        # Initialiser les catégories par défaut
        init_db()
        return "Base de données réinitialisée avec succès"
    except Exception as e:
        return f"Erreur lors de la réinitialisation : {str(e)}", 500

@app.route('/get-csrf-token')
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

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

@app.route('/admin/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_comment(comment_id):
    comment = db_session.query(Comment).filter_by(id=comment_id).first()
    if not comment:
        flash('Commentaire non trouvé.', 'error')
        return redirect(url_for('manage_comments'))
    
    try:
        # Si l'attribut is_approved n'existe pas, on l'ajoute
        if not hasattr(Comment, 'is_approved'):
            # Ajouter la colonne is_approved à la table Comment
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE comment ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE'))
                conn.commit()
        
        # Inverser le statut d'approbation
        comment.is_approved = not comment.is_approved
        db_session.commit()
        
        status = 'approuvé' if comment.is_approved else 'désapprouvé'
        flash(f'Le commentaire a été {status}.', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la modification du statut du commentaire.', 'error')
        print(f"Erreur lors de la modification du statut du commentaire : {e}")
    
    return redirect(url_for('manage_comments'))

@app.route('/admin/users/<int:user_id>/toggle-block', methods=['POST'])
@login_required
@admin_required
def toggle_user_block(user_id):
    # Empêcher un utilisateur de se bloquer lui-même
    if user_id == current_user.id:
        flash('Vous ne pouvez pas bloquer votre propre compte.', 'error')
        return redirect(url_for('manage_users'))
    
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        flash('Utilisateur non trouvé.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        # Inverser le statut de blocage
        user.is_blocked = not user.is_blocked
        db_session.commit()
        
        status = 'débloqué' if not user.is_blocked else 'bloqué'
        flash(f'L\'utilisateur a été {status}.', 'success')
    except Exception as e:
        db_session.rollback()
        flash('Erreur lors de la modification du statut de l\'utilisateur.', 'error')
        print(f"Erreur lors de la modification du statut de l'utilisateur : {e}")
    
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    with app.app_context():
        # Initialiser la base de données
        init_db()
    
    # Déterminer le port en fonction de l'environnement
    port = int(os.getenv('PORT', 8050))
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    app.run(host=host, port=port, debug=(os.getenv('FLASK_ENV') != 'production'))