from flask import  render_template, current_app, g
from models.article import Article
from models.category import Category
from models.user import User
from models.base import SessionLocal
from sqlalchemy import func
from bleach import clean
from flask import Blueprint
import html2text
from flask import request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from flask_mail import Message
import os
from schema_pydantic.schemas_pda import LoginForm, RegisterForm
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import string
from models.base import Base, engine
from models.page_view import PageView
from schema_pydantic.schemas_pda import ResetPasswordRequestForm
import secrets
from utils.email import send_admin_code

main_bp = Blueprint('main', __name__)

WTF_CSRF_ENABLED=True
WTF_CSRF_SECRET_KEY=os.environ.get('WTF_CSRF_SECRET_KEY', os.environ.get('SECRET_KEY'))
MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT=int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME=os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')

def generate_session_code():
    return ''.join(random.choices(string.digits, k=6))

def send_admin_verification_email(user_email, session_code):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
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
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.set_debuglevel(1)  # Activer le mode debug pour voir les détails de la connexion
        server.starttls()
        
        # Vérifier que les identifiants sont présents
        if not MAIL_USERNAME or not MAIL_PASSWORD:
            print("Erreur: Identifiants SMTP manquants")
            print(f"MAIL_USERNAME: {'Présent' if MAIL_USERNAME else 'Manquant'}")
            print(f"MAIL_PASSWORD: {'Présent' if MAIL_PASSWORD else 'Manquant'}")
            return False

        # Connexion au serveur
        print(f"Tentative de connexion à {MAIL_SERVER}:{MAIL_PORT}")
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        
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
    
@main_bp.route('/')
def index():
    # Récupérer les articles avec leurs relations
    articles = g.db.query(
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

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Gestion AJAX admin
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            is_admin = data.get('is_admin', False)
            admin_email = current_app.config['MAIL_USERNAME']
            
            if is_admin and email and email == admin_email:
                session_code = generate_session_code()
                session['admin_code'] = session_code
                session['admin_code_expiry'] = datetime.now().replace(tzinfo=None) + timedelta(minutes=15)
                session['admin_email'] = email
                
                if send_admin_code(
                    admin_email=email,
                    admin_name="Administrateur",
                    admin_code=session_code
                ):
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
        user = g.db.query(User).filter_by(email=email).first()
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
            return redirect(url_for('main.index'))
        if error:
            flash(error, 'error')
            # Ajouter un message d'aide si l'email existe mais le mot de passe est incorrect
            if user is not None and not check_password_hash(user.password_hash, password):
                flash('Si vous avez oublié votre mot de passe, vous pouvez le réinitialiser en cliquant sur "Mot de passe oublié".', 'info')
    form = LoginForm()
    return render_template('login.html', form=form)

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        error = None

        if g.db.query(User).filter_by(email=email).first():
            error = 'Un compte avec cet email existe déjà.'
        elif g.db.query(User).filter_by(username=username).first():
            error = 'Ce nom d\'utilisateur est déjà pris.'

        if error is None:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False,
                is_blocked=False
            )
            g.db.add(user)
            g.db.commit()
            
            # Envoyer l'email de bienvenue
            try:
                msg = Message(
                    subject="Bienvenue sur PowerDataLab !",
                    recipients=[email],
                    html=render_template('email/welcome.html',
                                       username=username,
                                       login_url=url_for('main.login', _external=True),
                                       now=datetime.now())  # Ajout de la variable now
                )
                current_app.mail.send(msg)
                flash('Un email de bienvenue vous a été envoyé !', 'success')
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email de bienvenue : {e}")
                # On continue même si l'email échoue
            
            login_user(user)
            flash('Compte créé avec succès!', 'success')
            return redirect(url_for('main.index'))

        flash(error, 'error')
    return render_template('register.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/about')
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
    g.db.add(page_view)
    g.db.commit()
    
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
            current_app.mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    return render_template('about.html')

@main_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = g.db.query(User).filter_by(email=form.email.data).first()
        
        if user:
            # Générer un token unique
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            
            # Sauvegarder le token dans la base de données
            user.reset_token = token
            user.reset_token_expiry = expiry
            g.db.commit()
            
            # Envoyer l'email
            reset_url = url_for('main.reset_password', token=token, _external=True)
            msg = Message(
                'Réinitialisation de votre mot de passe',
                recipients=[form.email.data],
                html=render_template('email/reset_password.html', 
                                   reset_url=reset_url,
                                   username=user.username)
            )
            try:
                current_app.mail.send(msg)
                flash('Un email avec les instructions de réinitialisation a été envoyé.', 'info')
            except Exception as e:
                flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'error')
                print(f"Erreur d'envoi d'email: {e}")
        else:
            # Pour des raisons de sécurité, on affiche le même message même si l'email n'existe pas
            flash('Si votre email est enregistré, vous recevrez les instructions de réinitialisation.', 'info')
        
        return redirect(url_for('main.login'))
    
    return render_template('reset_password_request.html', form=form)


@main_bp.route('/reset-db')
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
        current_app.init_db()
        return "Base de données réinitialisée avec succès"
    except Exception as e:
        return f"Erreur lors de la réinitialisation : {str(e)}", 500
