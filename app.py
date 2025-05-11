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
import sqlite3
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

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.is_admin = bool(user_data['is_admin'])
        self.password_hash = user_data['password_hash']

    @staticmethod
    def get(user_id):
        user_data = get_user_by_id(user_id)
        if user_data:
            return User(user_data)
        return None

# Chargement des variables d'environnement
load_dotenv()
print("Variables d'environnement chargées :")
print(f"MAIL_SERVER: {os.environ.get('MAIL_SERVER')}")
print(f"MAIL_PORT: {os.environ.get('MAIL_PORT')}")
print(f"MAIL_USE_TLS: {os.environ.get('MAIL_USE_TLS')}")
print(f"MAIL_USERNAME: {os.environ.get('MAIL_USERNAME')}")
print(f"MAIL_PASSWORD: {'Présent' if os.environ.get('MAIL_PASSWORD') else 'Manquant'}")
print(f"MAIL_DEFAULT_SENDER: {os.environ.get('MAIL_DEFAULT_SENDER')}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['DATABASE'] = 'blog.db'

# Configuration CSRF
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', 'your-csrf-secret-key-here')

# Configuration de Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read())
        db.commit()

# Initialisation des extensions
mail = Mail(app)

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Création des dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Fonctions de gestion des utilisateurs
def get_user_by_id(user_id):
    cur = get_db().execute('SELECT * FROM users WHERE id = ?', [user_id])
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return dict(user_data)
    return None

def get_user_by_email(email):
    cur = get_db().execute('SELECT * FROM users WHERE email = ?', [email])
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return dict(user_data)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Vérifier d'abord si c'est l'email admin
        if email == os.getenv('MAIL_USERNAME'):
            session_code = generate_session_code()
            session['admin_code'] = session_code
            session['admin_code_expiry'] = datetime.now().replace(tzinfo=None) + timedelta(minutes=15)
            session['admin_email'] = email
            
            if send_admin_verification_email(email, session_code):
                flash('Un code de vérification a été envoyé à votre email.', 'info')
                return redirect(url_for('admin_verify'))
            else:
                flash('Erreur lors de l\'envoi du code de vérification.', 'error')
                return redirect(url_for('login'))
        
        # Pour les utilisateurs normaux, vérifier le mot de passe
        user_data = get_user_by_email(email)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            session['is_admin'] = user.is_admin
            flash('Connexion réussie!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
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
@app.route('/')
def index():
    # Enregistrer la visite
    page_view = {
        'page': 'home',
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string,
        'referrer': request.referrer,
        'is_bot': request.user_agent.browser is None,
        'viewed_at': datetime.now()
    }
    get_db().execute('INSERT INTO page_views (page, ip_address, user_agent, referrer, is_bot) VALUES (?, ?, ?, ?, ?)',
               (page_view['page'], page_view['ip_address'], page_view['user_agent'], page_view['referrer'], page_view['is_bot']))
    get_db().commit()
    
    # Envoyer une notification si c'est une visite humaine et que ce n'est pas l'admin connecté
    if not page_view['is_bot'] and (not current_user.is_authenticated or current_user['email'] != os.getenv('MAIL_USERNAME')):
        try:
            msg = Message(
                subject="Nouvelle visite sur votre blog",
                recipients=[os.getenv('MAIL_USERNAME')],
                html=f"""
                <h2>Nouvelle visite sur votre blog</h2>
                <p>Une nouvelle personne a visité la page d'accueil de votre blog.</p>
                <ul>
                    <li>Date et heure : {page_view['viewed_at']}</li>
                    <li>Navigateur : {request.user_agent.browser}</li>
                    <li>Plateforme : {request.user_agent.platform}</li>
                    <li>Provenance : {request.referrer or 'Accès direct'}</li>
                </ul>
                """
            )
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    cur = get_db().execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
    ''')
    articles = [dict(row) for row in cur.fetchall()]
    
    cur = get_db().execute('SELECT * FROM categories')
    categories = [dict(row) for row in cur.fetchall()]
    
    # Ajouter le nombre d'articles par catégorie
    for category in categories:
        cur = get_db().execute('SELECT COUNT(*) as count FROM articles WHERE category_id = ?', [category['id']])
        category['article_count'] = cur.fetchone()['count']
    
    return render_template('blog.html', articles=articles, categories=categories)

@app.route('/about')
def about():
    # Enregistrer la visite
    page_view = {
        'page': 'about',
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string,
        'referrer': request.referrer,
        'is_bot': request.user_agent.browser is None,
        'viewed_at': datetime.now()
    }
    get_db().execute('INSERT INTO page_views (page, ip_address, user_agent, referrer, is_bot) VALUES (?, ?, ?, ?, ?)',
               (page_view['page'], page_view['ip_address'], page_view['user_agent'], page_view['referrer'], page_view['is_bot']))
    get_db().commit()
    
    # Envoyer une notification par email si c'est une visite humaine et que ce n'est pas l'admin connecté
    if not page_view['is_bot'] and (not current_user.is_authenticated or current_user['email'] != os.getenv('MAIL_USERNAME')):
        try:
            msg = Message(
                subject="Nouvelle visite sur votre page À propos",
                recipients=[os.getenv('MAIL_USERNAME')],
                html=f"""
                <h2>Nouvelle visite sur votre page À propos</h2>
                <p>Une nouvelle personne a visité votre page À propos.</p>
                <ul>
                    <li>Date et heure : {page_view['viewed_at']}</li>
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
    cur = get_db().execute('SELECT * FROM categories WHERE slug = ?', [slug])
    category_data = cur.fetchone()
    
    if category_data is None:
        return abort(404)
    
    category = dict(category_data)
    
    # Enregistrer la visite
    page_view = {
        'page': 'category',
        'page_id': category['id'],
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string,
        'referrer': request.referrer,
        'is_bot': request.user_agent.browser is None,
        'viewed_at': datetime.now()
    }
    get_db().execute('INSERT INTO page_views (page, page_id, ip_address, user_agent, referrer, is_bot) VALUES (?, ?, ?, ?, ?, ?)',
               (page_view['page'], page_view['page_id'], page_view['ip_address'], page_view['user_agent'], page_view['referrer'], page_view['is_bot']))
    get_db().commit()
    
    # Envoyer une notification si c'est une visite humaine et que ce n'est pas l'admin connecté
    if not page_view['is_bot'] and (not current_user.is_authenticated or current_user['email'] != os.getenv('MAIL_USERNAME')):
        try:
            msg = Message(
                subject=f"Nouvelle visite sur la catégorie : {category['name']}",
                recipients=[os.getenv('MAIL_USERNAME')],
                html=f"""
                <h2>Nouvelle visite sur votre catégorie</h2>
                <p>Une nouvelle personne a visité la catégorie : {category['name']}</p>
                <ul>
                    <li>Date et heure : {page_view['viewed_at']}</li>
                    <li>Navigateur : {request.user_agent.browser}</li>
                    <li>Plateforme : {request.user_agent.platform}</li>
                    <li>Provenance : {request.referrer or 'Accès direct'}</li>
                </ul>
                <p><a href="{url_for('category', slug=category['slug'], _external=True)}">Voir la catégorie</a></p>
                """
            )
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    cur = get_db().execute('''
        SELECT articles.*, categories.name as category_name, categories.slug as category_slug, categories.color_theme, users.username as author_name
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        WHERE articles.category_id = ?
        ORDER BY articles.created_at DESC
    ''', [category['id']])
    articles = [dict(row) for row in cur.fetchall()]
    
    cur = get_db().execute('SELECT * FROM categories')
    categories = [dict(row) for row in cur.fetchall()]
    
    # Ajouter le nombre d'articles par catégorie
    for cat in categories:
        cur = get_db().execute('SELECT COUNT(*) as count FROM articles WHERE category_id = ?', [cat['id']])
        cat['article_count'] = cur.fetchone()['count']
    
    return render_template('category.html', articles=articles, category=category, categories=categories)

@app.route('/article/<slug>')
def article(slug):
    cur = get_db().execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        WHERE articles.slug = ?
    ''', [slug])
    article_data = cur.fetchone()
    
    if article_data is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('index'))
    
    article = dict(article_data)
    return render_template('article.html', article=article)

# Routes d'administration
@app.route('/admin')
@login_required
@admin_required
def admin():
    # Récupérer les articles récents
    cur = get_db().execute('''
        SELECT articles.*, categories.name as category_name, categories.color_theme, users.username as author_name
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
    ''')
    articles = cur.fetchall()
    
    # Récupérer les catégories
    cur = get_db().execute('SELECT * FROM categories')
    categories = cur.fetchall()
    
    # Récupérer les commentaires récents
    cur = get_db().execute('''
        SELECT comments.*, articles.title as article_title, users.username as author_name
        FROM comments 
        LEFT JOIN articles ON comments.article_id = articles.id
        LEFT JOIN users ON comments.user_id = users.id
        ORDER BY comments.created_at DESC
    ''')
    comments = cur.fetchall()
    
    return render_template('admin/dashboard.html',
                         articles=articles,
                         categories=categories,
                         comments=comments)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Récupérer les articles récents
    cur = get_db().execute('''
        SELECT articles.*, categories.name as category_name, categories.color_theme, users.username as author_name
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
    ''')
    articles = [dict(row) for row in cur.fetchall()]
    
    # Récupérer les catégories
    cur = get_db().execute('SELECT * FROM categories')
    categories = [dict(row) for row in cur.fetchall()]
    
    # Récupérer les commentaires récents
    cur = get_db().execute('''
        SELECT comments.*, articles.title as article_title, users.username as author_name
        FROM comments 
        LEFT JOIN articles ON comments.article_id = articles.id
        LEFT JOIN users ON comments.user_id = users.id
        ORDER BY comments.created_at DESC
    ''')
    comments = [dict(row) for row in cur.fetchall()]
    
    # Statistiques
    cur = get_db().execute('SELECT COUNT(*) as count FROM articles')
    total_articles = cur.fetchone()['count']
    
    cur = get_db().execute('SELECT COUNT(*) as count FROM comments')
    total_comments = cur.fetchone()['count']
    
    cur = get_db().execute('SELECT COUNT(*) as count FROM users')
    total_users = cur.fetchone()['count']
    
    return render_template('admin/dashboard.html',
                         articles=articles,
                         categories=categories,
                         comments=comments,
                         total_articles=total_articles,
                         total_comments=total_comments,
                         total_users=total_users)

class ArticleForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    category = SelectField('Catégorie', coerce=int, validators=[DataRequired()])
    images = FileField('Images', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    tags = StringField('Tags')
    
    def __init__(self, *args, **kwargs):
        super(ArticleForm, self).__init__(*args, **kwargs)
        self.category.choices = [(c['id'], c['name']) for c in get_all_categories()]

@app.route('/admin/create-article', methods=['GET', 'POST'])
@login_required
@admin_required
def create_article():
    form = ArticleForm()
    
    if form.validate_on_submit():
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
                    # Remplacer les antislashs par des slashs
                    rel_path = os.path.join('uploads', filename).replace('\\', '/')
                    image_paths.append(rel_path)
        
        slug = slugify(title)
        image_path = ','.join(image_paths) if image_paths else None
        
        get_db().execute('''
            INSERT INTO articles (title, slug, content, category_id, user_id, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [title, slug, content, category_id, current_user.id, image_path])
        get_db().commit()
        
        flash('Article créé avec succès !', 'success')
        return redirect(url_for('manage_articles'))
    
    return render_template('admin/article_form.html', form=form)

# Route pour la newsletter
@app.route('/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if email:
        cur = get_db().execute('SELECT * FROM newsletter_subscribers WHERE email = ?', [email])
        subscriber = cur.fetchone()
        cur.close()
        if not subscriber:
            get_db().execute('''
                INSERT INTO newsletter_subscribers (email, confirmed)
                VALUES (?, 0)
            ''', [email])
            get_db().commit()
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

    # Récupérer les abonnés avec pagination
    cur = get_db().execute('''
        SELECT COUNT(*) as count FROM newsletter_subscribers
    ''')
    total_subscribers = cur.fetchone()['count']
    
    cur = get_db().execute('''
        SELECT * FROM newsletter_subscribers
        ORDER BY subscribed_at DESC
        LIMIT ? OFFSET ?
    ''', [per_page, (page - 1) * per_page])
    subscribers = cur.fetchall()
    
    # Récupérer les articles récents pour le formulaire d'envoi
    cur = get_db().execute('''
        SELECT articles.*, categories.name as category_name, categories.color_theme, users.username as author_name
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
        LIMIT 5
    ''')
    recent_articles = cur.fetchall()
    
    # Récupérer l'historique des newsletters
    cur = get_db().execute('''
        SELECT 
            nh.*,
            users.username as sender_name,
            strftime('%d/%m/%Y %H:%M', nh.sent_at) as sent_at_formatted
        FROM newsletter_history nh
        LEFT JOIN users ON nh.sent_by = users.id
        ORDER BY nh.sent_at DESC
        LIMIT 10
    ''')
    newsletter_history = cur.fetchall()
    
    # Créer l'objet de pagination pour les abonnés
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
        # Récupérer les articles sélectionnés
        articles = []
        if article_ids:
            cur = get_db().execute('''
                SELECT * FROM articles
                WHERE id IN ({})
            '''.format(','.join(['?'] * len(article_ids))), article_ids)
            articles = cur.fetchall()
        
        # Préparer le contenu HTML avec les articles
        html_content = content
        if articles:
            html_content += '<h2>Articles récents</h2>'
            for article in articles:
                excerpt = article['content'][:200] + '...' if len(article['content']) > 200 else article['content']
                html_content += f'''
                <div style="margin-bottom: 20px;">
                    <h3>{article['title']}</h3>
                    <p>{excerpt}</p>
                    <a href="{url_for('article', slug=article['slug'], _external=True)}">Lire la suite</a>
                </div>
                '''

        recipient_count = 0
        if test_send:
            # Envoyer un test à l'administrateur
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
            # Déterminer les destinataires en fonction du type de sélection
            if recipient_type == 'all':
                cur = get_db().execute('''
                    SELECT id, email FROM newsletter_subscribers
                    WHERE status = 'active'
                ''')
                subscribers = cur.fetchall()
            else:
                if not selected_subscribers:
                    return jsonify({'success': False, 'message': 'Aucun destinataire sélectionné'})
                
                cur = get_db().execute('''
                    SELECT id, email FROM newsletter_subscribers
                    WHERE id IN ({}) AND status = 'active'
                '''.format(','.join(['?'] * len(selected_subscribers))), selected_subscribers)
                subscribers = cur.fetchall()
            
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
                            recipients=[subscriber['email']],
                            html=html_content
                        )
                        mail.send(msg)
                        get_db().execute('''
                            UPDATE newsletter_subscribers
                            SET last_newsletter = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', [subscriber['id']])
                        success_count += 1
                    except Exception as e:
                        print(f"Erreur lors de l'envoi à {subscriber['email']}: {str(e)}")
                        error_count += 1
                        continue
                
                recipient_count = success_count
                message = f'Newsletter envoyée à {success_count} destinataire(s)'
                if error_count > 0:
                    message += f' ({error_count} échec(s))'

        # Sauvegarder l'historique de la newsletter
        get_db().execute('''
            INSERT INTO newsletter_history 
            (subject, content, sent_by, recipient_count, test_send)
            VALUES (?, ?, ?, ?, ?)
        ''', [subject, html_content, current_user.id, recipient_count, test_send])
        get_db().commit()

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        print(f"Erreur lors de l'envoi de la newsletter: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

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
                cur = get_db().execute('SELECT * FROM newsletter_subscribers WHERE email = ?', [row['email']])
                existing = cur.fetchone()
                if not existing:
                    get_db().execute('''
                        INSERT INTO newsletter_subscribers (email, status, subscribed_at)
                        VALUES (?, 'active', CURRENT_TIMESTAMP)
                    ''', [row['email']])
                    count += 1

        get_db().commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/newsletter/export')
@login_required
@admin_required
def export_subscribers():
    try:
        # Créer un fichier CSV en mémoire
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['email', 'status', 'subscribed_at', 'last_newsletter'])

        cur = get_db().execute('''
            SELECT email, status, subscribed_at, last_newsletter
            FROM newsletter_subscribers
        ''')
        subscribers = cur.fetchall()
        for subscriber in subscribers:
            writer.writerow([
                subscriber['email'],
                subscriber['status'],
                subscriber['subscribed_at'].strftime('%Y-%m-%d %H:%M:%S'),
                subscriber['last_newsletter'].strftime('%Y-%m-%d %H:%M:%S') if subscriber['last_newsletter'] else ''
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
    cur = get_db().execute('SELECT * FROM newsletter_subscribers WHERE id = ?', [subscriber_id])
    subscriber = cur.fetchone()
    if subscriber is None:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    
    try:
        get_db().execute('DELETE FROM newsletter_subscribers WHERE id = ?', [subscriber_id])
        get_db().commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/newsletter/subscribers/<int:subscriber_id>/<action>', methods=['POST'])
@login_required
@admin_required
def toggle_subscriber_status(subscriber_id, action):
    if action not in ['unsubscribe', 'resubscribe']:
        return jsonify({'success': False, 'message': 'Action invalide'})

    cur = get_db().execute('SELECT * FROM newsletter_subscribers WHERE id = ?', [subscriber_id])
    subscriber = cur.fetchone()
    if subscriber is None:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    
    try:
        if action == 'unsubscribe':
            get_db().execute('UPDATE newsletter_subscribers SET status = ? WHERE id = ?', ['unsubscribed', subscriber_id])
        else:
            get_db().execute('UPDATE newsletter_subscribers SET status = ? WHERE id = ?', ['active', subscriber_id])
        get_db().commit()
        return jsonify({'success': True})
    except Exception as e:
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

@app.route('/admin/verify', methods=['GET'])
def admin_verify():
    if not session.get('admin_email'):
        return redirect(url_for('login'))
    return render_template('admin_verify.html')

@app.route('/admin/verify-code', methods=['POST'])
def verify_admin_code():
    if not session.get('admin_email'):
        return redirect(url_for('login'))
    
    code = request.form.get('code')
    stored_code = session.get('admin_code')
    expiry_time = session.get('admin_code_expiry')
    
    if stored_code and expiry_time and isinstance(expiry_time, datetime):
        current_time = datetime.now().replace(tzinfo=None)
        expiry_time = expiry_time.replace(tzinfo=None)
        
        if current_time < expiry_time:
            if code == stored_code:
                # Vérifier si l'utilisateur admin existe déjà
                cur = get_db().execute('SELECT * FROM users WHERE email = ?', [session['admin_email']])
                user_data = cur.fetchone()
                
                if user_data:
                    user = User(dict(user_data))
                else:
                    # Créer un nouvel utilisateur admin
                    password_hash = generate_password_hash(''.join(random.choices(string.ascii_letters + string.digits, k=12)))
                    get_db().execute('''
                        INSERT INTO users (username, email, password_hash, is_admin)
                        VALUES (?, ?, ?, 1)
                    ''', ['admin', session['admin_email'], password_hash])
                    get_db().commit()
                    
                    # Récupérer l'utilisateur nouvellement créé
                    cur = get_db().execute('SELECT * FROM users WHERE email = ?', [session['admin_email']])
                    user_data = cur.fetchone()
                    user = User(dict(user_data))
                
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
        cur = get_db().execute('SELECT * FROM categories')
        g.categories = [dict(row) for row in cur.fetchall()]

@app.context_processor
def inject_categories():
    return dict(categories=g.get('categories', []))

class CSRFProtectForm(FlaskForm):
    pass

@app.route('/admin/articles')
@login_required
@admin_required
def manage_articles():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    form = CSRFProtectForm()

    # Compter le nombre total d'articles
    cur = get_db().execute('SELECT COUNT(*) as count FROM articles')
    total = cur.fetchone()['count']
    
    # Récupérer les articles avec pagination
    cur = get_db().execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id,
            strftime('%d/%m/%Y', articles.created_at) as created_at_formatted
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
        LIMIT ? OFFSET ?
    ''', [per_page, (page - 1) * per_page])
    articles = cur.fetchall()
    
    # Créer l'objet de pagination
    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': articles
    })
    
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
        # Format attendu: YYYYMMDD_HHMMSS_nom_fichier.ext
        parts = filename.split('_')
        if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:  # Format timestamp
            # Reconstruire le nom sans le timestamp
            base_name = '_'.join(parts[2:])
        else:
            # Si le format n'est pas un timestamp, garder le nom complet
            base_name = filename
            
        file_path = os.path.join(upload_dir, filename)
        mod_time = os.path.getmtime(file_path)
        print(f"Traitement du fichier: {filename}")
        print(f"  - Nom de base: {base_name}")
        print(f"  - Date de modification: {datetime.fromtimestamp(mod_time)}")
        
        # Si on a déjà vu ce fichier, garder le plus récent
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
    conn = get_db()
    cursor = conn.cursor()
    
    # Récupérer tous les articles avec des images
    cursor.execute('SELECT id, image_path FROM articles WHERE image_path IS NOT NULL')
    articles = cursor.fetchall()
    
    for article in articles:
        if not article['image_path']:
            continue
            
        # Séparer les chemins d'images
        image_paths = article['image_path'].split(',')
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
            cursor.execute('''
                UPDATE articles 
                SET image_path = ?
                WHERE id = ?
            ''', [','.join(valid_paths), article['id']])
            print(f"Article {article['id']} mis à jour avec {len(valid_paths)} images valides")
        else:
            cursor.execute('''
                UPDATE articles 
                SET image_path = NULL
                WHERE id = ?
            ''', [article['id']])
            print(f"Article {article['id']} mis à jour: aucune image valide")
    
    conn.commit()
    print("\nNettoyage terminé.")

@app.route('/admin/articles/new', methods=['GET', 'POST'])
@login_required
def new_article():
    if request.method == 'POST':
        print("Début de la création d'un nouvel article...")  # Log de début
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category_id']
        slug = slugify(title)
        
        # Gestion des images multiples
        image_paths = []
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
                        # Remplacer les antislashs par des slashs
                        rel_path = os.path.join('uploads', filename).replace('\\', '/')
                        image_paths.append(rel_path)
        # Nettoyer la liste (supprimer les vides)
        image_paths = [p for p in image_paths if p]
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO articles (title, slug, content, category_id, user_id, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (title, slug, content, category_id, current_user.id, ','.join(image_paths) if image_paths else None))
        conn.commit()
        
        # Nettoyer les images en double
        print("Appel de clean_duplicate_images après création d'article...")  # Log avant nettoyage
        clean_duplicate_images()
        print("Nettoyage terminé.")  # Log après nettoyage
        
        flash('Article créé avec succès !', 'success')
        return redirect(url_for('manage_articles'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    
    return render_template('admin/article_form.html', categories=categories)

@app.route('/admin/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    if request.method == 'POST':
        print("Début de la modification d'un article...")  # Log de début
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category_id']
        slug = slugify(title)
        
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
        
        get_db().execute('''
            UPDATE articles 
            SET title = ?, slug = ?, content = ?, category_id = ?, image_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, slug, content, category_id, ','.join(image_paths) if image_paths else None, article_id))
        get_db().commit()
        
        # Nettoyer les images en double
        print("Appel de clean_duplicate_images après modification d'article...")  # Log avant nettoyage
        clean_duplicate_images()
        print("Nettoyage terminé.")  # Log après nettoyage
        
        flash('Article modifié avec succès !', 'success')
        return redirect(url_for('manage_articles'))
    
    cur = get_db().execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id,
            strftime('%d/%m/%Y', articles.created_at) as created_at_formatted
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        WHERE articles.id = ?
    ''', (article_id,))
    article = dict(cur.fetchone())
    
    cur = get_db().execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(row) for row in cur.fetchall()]
    
    return render_template('admin/article_form.html', article=article, categories=categories)

@app.route('/admin/articles/delete/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def delete_article_route(article_id):
    db = get_db()
    try:
        # Vérifier si l'article existe
        cur = db.execute('SELECT * FROM articles WHERE id = ?', [article_id])
        article_data = cur.fetchone()
        
        if article_data is None:
            flash('Article non trouvé.', 'error')
            return redirect(url_for('manage_articles'))
        
        article = dict(article_data)
        
        # Supprimer l'image si elle existe
        if article['image_path']:
            try:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(article['image_path']))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Erreur lors de la suppression de l'image : {e}")
        
        # Supprimer l'article
        db.execute('DELETE FROM articles WHERE id = ?', [article_id])
        db.commit()
        
        flash('Article supprimé avec succès!', 'success')
    except Exception as e:
        db.rollback()
        flash('Erreur lors de la suppression de l\'article.', 'error')
        print(f"Erreur lors de la suppression de l'article : {e}")
    finally:
        db.close()
    
    return redirect(url_for('manage_articles'))

@app.route('/admin/comments')
@login_required
@admin_required
def manage_comments():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Compter le nombre total de commentaires
    cur = get_db().execute('SELECT COUNT(*) as count FROM comments')
    total = cur.fetchone()['count']
    
    # Récupérer les commentaires avec pagination
    cur = get_db().execute('''
        SELECT 
            comments.*,
            strftime('%d/%m/%Y %H:%M', comments.created_at) as created_at_formatted,
            articles.title as article_title,
            users.username as author_name
        FROM comments 
        LEFT JOIN articles ON comments.article_id = articles.id
        LEFT JOIN users ON comments.user_id = users.id
        ORDER BY comments.created_at DESC
        LIMIT ? OFFSET ?
    ''', [per_page, (page - 1) * per_page])
    comments = cur.fetchall()
    
    # Créer l'objet de pagination
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
    cur = get_db().execute('SELECT * FROM comments WHERE id = ?', [comment_id])
    comment_data = cur.fetchone()
    if comment_data is None:
        flash('Commentaire non trouvé.', 'error')
        return redirect(url_for('manage_comments'))
    
    get_db().execute('DELETE FROM comments WHERE id = ?', [comment_id])
    get_db().commit()
    flash('Commentaire supprimé avec succès!', 'success')
    return redirect(url_for('manage_comments'))

@app.route('/article/<slug>/comment', methods=['POST'])
@login_required
def add_comment(slug):
    cur = get_db().execute('''
        SELECT * FROM articles
        WHERE slug = ?
    ''', [slug])
    article_data = cur.fetchone()
    
    if article_data is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('index'))
    
    article = dict(article_data)
    content = request.form.get('content')
    if not content:
        flash('Le contenu du commentaire est requis.', 'error')
        return redirect(url_for('article', slug=slug))
    
    get_db().execute('''
        INSERT INTO comments (content, article_id, user_id)
        VALUES (?, ?, ?)
    ''', [content, article['id'], current_user.id])
    get_db().commit()
    flash('Commentaire ajouté avec succès!', 'success')
    return redirect(url_for('article', slug=slug))

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Compter le nombre total d'utilisateurs
    cur = get_db().execute('SELECT COUNT(*) as count FROM users')
    total = cur.fetchone()['count']
    
    # Récupérer les utilisateurs avec pagination
    cur = get_db().execute('''
        SELECT 
            users.*,
            strftime('%d/%m/%Y', users.created_at) as created_at_formatted,
            (SELECT COUNT(*) FROM articles WHERE articles.user_id = users.id) as article_count,
            (SELECT COUNT(*) FROM comments WHERE comments.user_id = users.id) as comment_count
        FROM users
        ORDER BY users.created_at DESC
        LIMIT ? OFFSET ?
    ''', [per_page, (page - 1) * per_page])
    users = cur.fetchall()
    
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
    
    return render_template('admin/manage_users.html', users=pagination, pagination=pagination)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    cur = get_db().execute('SELECT * FROM users WHERE id = ?', [user_id])
    user_data = cur.fetchone()
    if user_data is None:
        flash('Utilisateur non trouvé.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        get_db().execute('DELETE FROM users WHERE id = ?', [user_id])
        get_db().commit()
        flash('Utilisateur supprimé avec succès !', 'success')
    except Exception as e:
        flash('Erreur lors de la suppression de l\'utilisateur.', 'error')
    return redirect(url_for('manage_users'))

@app.route('/admin/update-categories')
@login_required
@admin_required
def update_categories():
    # Supprimer toutes les catégories existantes
    get_db().execute('DELETE FROM categories')
    
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
        get_db().execute('''
            INSERT INTO categories (name, slug, color_theme, description)
            VALUES (?, ?, ?, ?)
        ''', [data['name'], slug, data['color'], data['description']])
    
    try:
        get_db().commit()
        flash('Catégories mises à jour avec succès !', 'success')
    except Exception as e:
        get_db().rollback()
        flash('Erreur lors de la mise à jour des catégories.', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/newsletter/<int:newsletter_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_newsletter(newsletter_id):
    cur = get_db().execute('''
        SELECT * FROM newsletter
        WHERE id = ?
    ''', [newsletter_id])
    newsletter_data = cur.fetchone()
    
    if newsletter_data is None:
        flash('Newsletter non trouvée.', 'error')
        return redirect(url_for('manage_newsletter'))
    
    newsletter = dict(newsletter_data)
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        article_ids = request.form.getlist('articles')
        
        if not subject or not content:
            flash('Le sujet et le contenu sont requis.', 'error')
            return redirect(url_for('edit_newsletter', newsletter_id=newsletter_id))
        
        try:
            get_db().execute('''
                UPDATE newsletter
                SET subject = ?, content = ?, article_ids = ?
                WHERE id = ?
            ''', [subject, content, ','.join(map(str, article_ids)), newsletter_id])
            get_db().commit()
            flash('Newsletter modifiée avec succès !', 'success')
            return redirect(url_for('manage_newsletter'))
        except Exception as e:
            flash('Erreur lors de la modification de la newsletter.', 'error')
            return redirect(url_for('edit_newsletter', newsletter_id=newsletter_id))
    
    # Récupérer tous les articles pour le formulaire
    cur = get_db().execute('''
        SELECT * FROM articles
        ORDER BY created_at DESC
    ''')
    articles = cur.fetchall()
    
    # Convertir les IDs d'articles en liste
    selected_articles = newsletter['article_ids'].split(',') if newsletter['article_ids'] else []
    
    return render_template('admin/edit_newsletter.html', 
                         newsletter=newsletter, 
                         articles=articles,
                         selected_articles=selected_articles)

@app.route('/admin/categories')
@login_required
@admin_required
def manage_categories():
    cur = get_db().execute('SELECT * FROM categories')
    categories = cur.fetchall()
    return render_template('admin/manage_categories.html', categories=categories)

@app.route('/admin/categories/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_category():
    if request.method == 'POST':
        name = request.form.get('name')
        color_theme = request.form.get('color_theme')
        description = request.form.get('description')
        
        if not name or not color_theme:
            flash('Le nom et la couleur sont requis.', 'error')
            return redirect(url_for('manage_categories'))
        
        slug = slugify(name)
        
        try:
            get_db().execute('''
                INSERT INTO categories (name, slug, color_theme, description)
                VALUES (?, ?, ?, ?)
            ''', [name, slug, color_theme, description])
            get_db().commit()
            flash('Catégorie créée avec succès!', 'success')
        except Exception as e:
            flash('Erreur lors de la création de la catégorie.', 'error')
            print(f"Erreur: {e}")
        
        return redirect(url_for('manage_categories'))
    
    return render_template('admin/category_form.html')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    if request.method == 'POST':
        name = request.form.get('name')
        color_theme = request.form.get('color_theme')
        description = request.form.get('description')
        
        if not name or not color_theme:
            flash('Le nom et la couleur sont requis.', 'error')
            return redirect(url_for('manage_categories'))
        
        slug = slugify(name)
        
        try:
            get_db().execute('''
                UPDATE categories
                SET name = ?, slug = ?, color_theme = ?, description = ?
                WHERE id = ?
            ''', [name, slug, color_theme, description, category_id])
            get_db().commit()
            flash('Catégorie mise à jour avec succès!', 'success')
        except Exception as e:
            flash('Erreur lors de la modification de la catégorie.', 'error')
            print(f"Erreur: {e}")
        
        return redirect(url_for('manage_categories'))
    
    # Pour la requête GET, retourner les données de la catégorie en JSON
    cur = get_db().execute('SELECT * FROM categories WHERE id = ?', [category_id])
    category = cur.fetchone()
    
    if category is None:
        return jsonify({'error': 'Catégorie non trouvée'}), 404
    
    return jsonify({
        'name': category['name'],
        'color': category['color_theme'],
        'description': category['description']
    })

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category_route(category_id):
    cur = get_db().execute('SELECT * FROM categories WHERE id = ?', [category_id])
    category_data = cur.fetchone()
    if category_data is None:
        flash('Catégorie non trouvée.', 'error')
        return redirect(url_for('manage_categories'))
    
    category = dict(category_data)
    
    # Vérifier s'il y a des articles dans cette catégorie
    cur = get_db().execute('SELECT COUNT(*) as count FROM articles WHERE category_id = ?', [category_id])
    articles_count = cur.fetchone()['count']
    
    if articles_count > 0:
        flash('Impossible de supprimer cette catégorie car elle contient des articles.', 'error')
        return redirect(url_for('manage_categories'))
    
    get_db().execute('DELETE FROM categories WHERE id = ?', [category_id])
    get_db().commit()
    flash('Catégorie supprimée avec succès!', 'success')
    return redirect(url_for('manage_categories'))

@app.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    # Statistiques générales
    cur = get_db().execute('''
        SELECT COUNT(*) as total_views, COUNT(DISTINCT ip_address) as unique_visitors
        FROM page_views
    ''')
    stats = cur.fetchone()
    total_views = stats['total_views']
    unique_visitors = stats['unique_visitors']
    
    # Visites aujourd'hui
    today = datetime.utcnow().date()
    cur = get_db().execute('''
        SELECT COUNT(*) as today_views
        FROM page_views
        WHERE date(viewed_at) = ?
    ''', [today])
    today_views = cur.fetchone()['today_views']
    
    # Visites cette semaine
    week_start = today - timedelta(days=today.weekday())
    cur = get_db().execute('''
        SELECT COUNT(*) as week_views
        FROM page_views
        WHERE date(viewed_at) >= ? AND date(viewed_at) < ?
    ''', [week_start, today])
    week_views = cur.fetchone()['week_views']
    
    # Statistiques par page
    cur = get_db().execute('''
        SELECT page, COUNT(*) as views
        FROM page_views
        GROUP BY page
    ''')
    page_stats = [dict(row) for row in cur.fetchall()]
    
    # Statistiques des 7 derniers jours
    last_week = datetime.utcnow() - timedelta(days=7)
    cur = get_db().execute('''
        SELECT date(viewed_at) as date, COUNT(*) as views
        FROM page_views
        WHERE viewed_at >= ? AND viewed_at < ?
        GROUP BY date(viewed_at)
    ''', [last_week, datetime.utcnow()])
    daily_stats = [dict(row) for row in cur.fetchall()]
    
    # Statistiques des navigateurs
    cur = get_db().execute('''
        SELECT SUBSTRING(user_agent, 1, 50) as browser, COUNT(*) as count
        FROM page_views
        GROUP BY SUBSTRING(user_agent, 1, 50)
    ''')
    browser_stats = [dict(row) for row in cur.fetchall()]
    
    # Statistiques des sources de trafic
    cur = get_db().execute('''
        SELECT COALESCE(referrer, 'Direct') as source, COUNT(*) as count
        FROM page_views
        GROUP BY COALESCE(referrer, 'Direct')
    ''')
    referrer_stats = [dict(row) for row in cur.fetchall()]
    
    # Articles les plus vus
    cur = get_db().execute('''
        SELECT articles.*, COUNT(*) as views
        FROM articles
        LEFT JOIN page_views ON page_views.page = 'article' AND page_views.page_id = articles.id
        GROUP BY articles.id
        ORDER BY views DESC
        LIMIT 10
    ''')
    top_articles = [dict(row) for row in cur.fetchall()]
    
    # Catégories les plus vues
    cur = get_db().execute('''
        SELECT categories.*, COUNT(*) as views
        FROM categories
        LEFT JOIN articles ON articles.category_id = categories.id
        LEFT JOIN page_views ON page_views.page = 'category' AND page_views.page_id = categories.id
        GROUP BY categories.id
        ORDER BY views DESC
        LIMIT 10
    ''')
    top_categories = [dict(row) for row in cur.fetchall()]
    
    return render_template('admin/analytics.html',
                         total_views=total_views,
                         unique_visitors=unique_visitors,
                         today_views=today_views,
                         week_views=week_views,
                         page_stats=page_stats,
                         daily_stats=daily_stats,
                         browser_stats=browser_stats,
                         referrer_stats=referrer_stats,
                         top_articles=top_articles,
                         top_categories=top_categories)

"""@app.teardown_appcontext
def close_connection(exception):
    get_db().close()"""

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    get_db().execute(query, args)
    get_db().commit()

# Fonctions de gestion des articles
def get_all_articles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id,
            strftime('%d/%m/%Y', articles.created_at) as created_at_formatted
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        ORDER BY articles.created_at DESC
    ''')
    articles = cursor.fetchall()
    conn.close()
    return articles

def get_article_by_id(article_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id,
            strftime('%d/%m/%Y', articles.created_at) as created_at_formatted
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        WHERE articles.id = ?
    ''', (article_id,))
    article = cursor.fetchone()
    conn.close()
    return article

def get_article_by_slug(slug):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            articles.*,
            categories.name as category_name,
            categories.slug as category_slug,
            categories.color_theme,
            users.username as author_name,
            users.id as author_id,
            strftime('%d/%m/%Y', articles.created_at) as created_at_formatted
        FROM articles 
        LEFT JOIN categories ON articles.category_id = categories.id
        LEFT JOIN users ON articles.user_id = users.id
        WHERE articles.slug = ?
    ''', (slug,))
    article = cursor.fetchone()
    conn.close()
    return article

def create_article(title, slug, content, category_id, user_id, image_path=None):
    modify_db('''
        INSERT INTO articles (title, slug, content, category_id, user_id, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [title, slug, content, category_id, user_id, image_path])

def update_article(article_id, title, slug, content, category_id, image_path=None):
    if image_path:
        modify_db('''
            UPDATE articles 
            SET title = ?, slug = ?, content = ?, category_id = ?, image_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', [title, slug, content, category_id, image_path, article_id])
    else:
        modify_db('''
            UPDATE articles 
            SET title = ?, slug = ?, content = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', [title, slug, content, category_id, article_id])

def delete_article(article_id):
    modify_db('DELETE FROM articles WHERE id = ?', [article_id])

# Fonctions de gestion des catégories
def get_all_categories():
    return query_db('SELECT * FROM categories ORDER BY name')

def get_category_by_id(category_id):
    return query_db('SELECT * FROM categories WHERE id = ?', [category_id], one=True)

def get_category_by_slug(slug):
    return query_db('SELECT * FROM categories WHERE slug = ?', [slug], one=True)

def create_category(name, slug, color_theme, description):
    modify_db('''
        INSERT INTO categories (name, slug, color_theme, description)
        VALUES (?, ?, ?, ?)
    ''', [name, slug, color_theme, description])

def update_category(category_id, name, slug, color_theme, description):
    modify_db('''
        UPDATE categories 
        SET name = ?, slug = ?, color_theme = ?, description = ?
        WHERE id = ?
    ''', [name, slug, color_theme, description, category_id])

def delete_category(category_id):
    modify_db('DELETE FROM categories WHERE id = ?', [category_id])

# Fonctions de gestion des commentaires
def get_all_comments():
    return query_db('''
        SELECT comments.*, articles.title as article_title, users.username as author_name
        FROM comments 
        LEFT JOIN articles ON comments.article_id = articles.id
        LEFT JOIN users ON comments.user_id = users.id
        ORDER BY comments.created_at DESC
    ''')

def get_comments_by_article(article_id):
    return query_db('''
        SELECT comments.*, users.username as author_name
        FROM comments 
        LEFT JOIN users ON comments.user_id = users.id
        WHERE comments.article_id = ?
        ORDER BY comments.created_at DESC
    ''', [article_id])

def get_comment_by_id(comment_id):
    return query_db('''
        SELECT comments.*, articles.title as article_title, users.username as author_name
        FROM comments 
        LEFT JOIN articles ON comments.article_id = articles.id
        LEFT JOIN users ON comments.user_id = users.id
        WHERE comments.id = ?
    ''', [comment_id], one=True)

def create_comment(content, article_id, user_id):
    modify_db('''
        INSERT INTO comments (content, article_id, user_id)
        VALUES (?, ?, ?)
    ''', [content, article_id, user_id])

def update_comment(comment_id, content):
    modify_db('''
        UPDATE comments 
        SET content = ?
        WHERE id = ?
    ''', [content, comment_id])

def delete_comment(comment_id):
    modify_db('DELETE FROM comments WHERE id = ?', [comment_id])

# Fonctions de gestion des abonnés à la newsletter
def get_all_subscribers():
    return query_db('SELECT * FROM newsletter_subscribers ORDER BY created_at DESC')

def get_subscriber_by_email(email):
    return query_db('SELECT * FROM newsletter_subscribers WHERE email = ?', [email], one=True)

def create_subscriber(email):
    modify_db('''
        INSERT INTO newsletter_subscribers (email, confirmed)
        VALUES (?, 0)
    ''', [email])

def confirm_subscriber(email):
    modify_db('''
        UPDATE newsletter_subscribers 
        SET confirmed = 1
        WHERE email = ?
    ''', [email])

def delete_subscriber(email):
    modify_db('DELETE FROM newsletter_subscribers WHERE email = ?', [email])

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    if not email:
        flash('Email requis.', 'error')
        return redirect(url_for('index'))
    
    # Vérifier si l'email existe déjà
    subscriber = get_subscriber_by_email(email)
    if subscriber:
        if subscriber['confirmed']:
            flash('Vous êtes déjà inscrit à la newsletter!', 'info')
        else:
            flash('Un email de confirmation vous a déjà été envoyé.', 'info')
        return redirect(url_for('index'))
    
    try:
        create_subscriber(email)
        
        # Envoyer l'email de confirmation
        token = generate_confirmation_token(email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        
        msg = Message(
            'Confirmez votre inscription à la newsletter',
            recipients=[email],
            html=render_template('email/confirm_subscription.html', confirm_url=confirm_url)
        )
        mail.send(msg)
        
        flash('Un email de confirmation vous a été envoyé.', 'success')
    except Exception as e:
        flash('Erreur lors de l\'inscription. Veuillez réessayer.', 'error')
    
    return redirect(url_for('index'))

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('Le lien de confirmation est invalide ou a expiré.', 'error')
        return redirect(url_for('index'))
    
    subscriber = get_subscriber_by_email(email)
    if subscriber is None:
        flash('Email non trouvé.', 'error')
        return redirect(url_for('index'))
    
    if subscriber['confirmed']:
        flash('Email déjà confirmé.', 'info')
    else:
        confirm_subscriber(email)
        flash('Merci d\'avoir confirmé votre email!', 'success')
    
    return redirect(url_for('index'))

@app.route('/unsubscribe/<token>')
def unsubscribe(token):
    try:
        email = confirm_token(token)
    except:
        flash('Le lien de désabonnement est invalide ou a expiré.', 'error')
        return redirect(url_for('index'))
    
    subscriber = get_subscriber_by_email(email)
    if subscriber is None:
        flash('Email non trouvé.', 'error')
        return redirect(url_for('index'))
    
    delete_subscriber(email)
    flash('Vous avez été désabonné avec succès.', 'success')
    return redirect(url_for('index'))

@app.route('/admin/subscribers')
@login_required
@admin_required
def manage_subscribers():
    cur = get_db().execute('''
        SELECT * FROM newsletter_subscribers
        ORDER BY created_at DESC
    ''')
    subscribers = cur.fetchall()
    return render_template('admin/manage_subscribers.html', subscribers=subscribers)

@app.route('/admin/subscribers/delete/<path:email>', methods=['POST'])
@login_required
@admin_required
def delete_subscriber_route(email):
    cur = get_db().execute('SELECT * FROM newsletter_subscribers WHERE email = ?', [email])
    subscriber_data = cur.fetchone()
    if subscriber_data is None:
        flash('Abonné non trouvé.', 'error')
        return redirect(url_for('manage_subscribers'))
    
    delete_subscriber(email)
    flash('Abonné supprimé avec succès!', 'success')
    return redirect(url_for('manage_subscribers'))

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Mot de passe', validators=[DataRequired()])
    confirm_password = StringField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Vérifier si l'email existe déjà
        if get_user_by_email(form.email.data):
            flash('Cet email est déjà utilisé.', 'error')
            return render_template('register.html', form=form)
        
        # Créer le nouvel utilisateur
        password_hash = generate_password_hash(form.password.data)
        get_db().execute('''
            INSERT INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', [form.username.data, form.email.data, password_hash, 0])
        get_db().commit()
        
        flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/category-color/<slug>')
def get_category_color(slug):
    cur = get_db().execute('SELECT color_theme FROM categories WHERE slug = ?', [slug])
    category = cur.fetchone()
    
    if category:
        return jsonify({'color': category['color_theme']})
    return jsonify({'color': '#007bff'})  # Couleur par défaut si la catégorie n'est pas trouvée

@app.route('/admin/newsletter/<int:newsletter_id>/content')
@login_required
@admin_required
def get_newsletter_content(newsletter_id):
    try:
        cur = get_db().execute('''
            SELECT content FROM newsletter_history
            WHERE id = ?
        ''', [newsletter_id])
        newsletter = cur.fetchone()
        
        if newsletter:
            return jsonify({
                'success': True,
                'content': newsletter['content']
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

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        # Générer un nom de fichier unique
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
        
        # Sauvegarder le fichier
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Retourner l'URL de l'image
        image_url = url_for('static', filename=f'uploads/{unique_filename}')
        return jsonify({'location': image_url})
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    with app.app_context():
        # Initialiser la base de données
        init_db()
        
        # Vérifier si les catégories existent déjà
        cur = get_db().execute('SELECT COUNT(*) FROM categories')
        if cur.fetchone()[0] == 0:
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
                get_db().execute('''
                    INSERT INTO categories (name, slug, color_theme, description)
                    VALUES (?, ?, ?, ?)
                ''', [data['name'], slug, data['color'], data['description']])
            
            try:
                get_db().commit()
                print("Catégories créées avec succès !")
            except Exception as e:
                get_db().rollback()
                print(f"Erreur lors de la création des catégories : {e}")
    
    # Déterminer le port en fonction de l'environnement
    port = int(os.getenv('PORT', 8050))
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    app.run(host=host, port=port, debug=(os.getenv('FLASK_ENV') != 'production'))