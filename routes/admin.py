from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from models.article import Article
from models.category import Category
from models.user import User
from models.base import SessionLocal
from models.comment import Comment
from flask_login import login_required
from schema_pydantic.schemas_pda import ArticleForm
from datetime import datetime
from flask_mail import Message
import os
from utils.decorateur import login_required, admin_required
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from models.page_view import PageView
from models.newsletter import NewsletterSubscriber, NewsletterHistory
from flask import Blueprint
from werkzeug.security import generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
import random
import string
from flask_login import login_user, current_user
from flask import session
from werkzeug.utils import secure_filename
from slugify import slugify
from flask import jsonify
from routes.main import generate_session_code, send_admin_verification_email
from io import StringIO
import csv
from flask import Response, current_app
from io import TextIOWrapper
from sqlalchemy import text
from sqlalchemy import or_
from flask_wtf.csrf import generate_csrf
from utils.email import send_admin_code

admin_bp = Blueprint('admin', __name__)


# Routes d'administration
@admin_bp.route('/admin')
@login_required
@admin_required
def admin():
    # Récupérer les articles récents avec leurs relations
    articles_query = g.db.query(
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
    categories = g.db.query(Category).all()
    
    # Récupérer les commentaires récents avec leurs relations
    comments_query = g.db.query(
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


@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Récupérer les articles récents avec leurs relations
    articles_query = g.db.query(
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
    categories = g.db.query(Category).all()
    
    # Récupérer les commentaires récents avec leurs relations
    comments_query = g.db.query(
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
    total_articles = g.db.query(Article).count()
    total_comments = g.db.query(Comment).count()
    total_users = g.db.query(User).count()
    
    # Statistiques des visites
    today = datetime.utcnow().date()
    today_views = g.db.query(PageView).filter(
        func.date(PageView.viewed_at) == today
    ).count()
    
    # Statistiques des abonnés
    total_subscribers = g.db.query(NewsletterSubscriber).count()
    active_subscribers = g.db.query(NewsletterSubscriber).filter_by(status='active').count()
    
    # Dernières newsletters envoyées
    recent_newsletters = g.db.query(NewsletterHistory).order_by(
        NewsletterHistory.sent_at.desc()
    ).limit(5).all()
    
    # Articles les plus vus cette semaine
    week_start = today - timedelta(days=today.weekday())
    top_articles_query = g.db.query(
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

@admin_bp.route('/admin/articles/create', methods=['GET', 'POST'])
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
                        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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
            g.db.add(article)
            g.db.commit()
            
            flash('Article créé avec succès !', 'success')
            return redirect(url_for('article.manage_articles'))
        except Exception as e:
            g.db.rollback()
            flash('Erreur lors de la création de l\'article.', 'error')
            print(f"Erreur lors de la création de l'article : {e}")
    
    return render_template('admin/article_form.html', form=form)

# Route pour la newsletter
@admin_bp.route('/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if email:
        subscriber = g.db.query(NewsletterSubscriber).filter_by(email=email).first()
        if not subscriber:
            subscriber = NewsletterSubscriber(
                email=email,
                status='pending',
                subscribed_at=datetime.now()
            )
            g.db.add(subscriber)
            g.db.commit()
            flash('Inscription à la newsletter réussie !', 'success')
        else:
            flash('Vous êtes déjà inscrit à la newsletter.', 'info')
    return redirect(url_for('main.index'))

# Routes pour la gestion de la newsletter
@admin_bp.route('/admin/newsletter')
@login_required
@admin_required
def manage_newsletter():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Récupérer tous les destinataires potentiels (utilisateurs et abonnés)
    all_recipients = []
    
    # Ajouter les utilisateurs actifs
    users = g.db.query(User).filter_by(is_active=True).all()
    for user in users:
        if user.email:  # Vérifier que l'email existe
            all_recipients.append({
                'id': f'user_{user.id}',  # Préfixe pour distinguer les utilisateurs
                'email': user.email,
                'type': 'user',
                'status': 'active',
                'name': user.username,
                'subscribed_at': user.created_at
            })
    
    # Ajouter les abonnés newsletter
    subscribers = g.db.query(NewsletterSubscriber).all()
    for subscriber in subscribers:
        all_recipients.append({
            'id': f'subscriber_{subscriber.id}',  # Préfixe pour distinguer les abonnés
            'email': subscriber.email,
            'type': 'subscriber',
            'status': subscriber.status,
            'name': None,
            'subscribed_at': subscriber.subscribed_at
        })
    
    # Trier par email pour faciliter la recherche
    all_recipients.sort(key=lambda x: x['email'])
    
    # Pagination manuelle
    total_items = len(all_recipients)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_page_items = all_recipients[start_idx:end_idx]
    
    pagination = type('Pagination', (), {
        'page': page,
        'pages': (total_items + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': end_idx < total_items,
        'prev_num': page - 1,
        'next_num': page + 1,
        'items': current_page_items
    })

    recent_articles = g.db.query(Article).order_by(Article.created_at.desc()).limit(5).all()
    newsletter_history = g.db.query(NewsletterHistory).order_by(NewsletterHistory.sent_at.desc()).limit(10).all()
    
    return render_template('admin/manage_newsletter.html', 
                         subscribers=pagination,
                         recent_articles=recent_articles,
                         newsletter_history=newsletter_history)

@admin_bp.route('/admin/newsletter/send', methods=['POST'])
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
            articles = g.db.query(Article).filter(Article.id.in_(article_ids)).all()
        html_content = content
        if articles:
            html_content += '<h2>Articles récents</h2>'
            for article in articles:
                excerpt = article.content[:200] + '...' if len(article.content) > 200 else article.content
                html_content += f'''
                <div style="margin-bottom: 20px;">
                    <h3>{article.title}</h3>
                    <p>{excerpt}</p>
                    <a href="{url_for('article.article', slug=article.slug, _external=True)}">Lire la suite</a>
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
            current_app.extensions['mail'].send(msg)
            recipient_count = 1
            message = 'Email de test envoyé à l\'administrateur'
        else:
            all_recipients = set()  # Utiliser un set pour éviter les doublons d'emails
            
            if recipient_type == 'all':
                # Récupérer tous les abonnés actifs à la newsletter
                newsletter_subscribers = g.db.query(NewsletterSubscriber).filter_by(status='active').all()
                for subscriber in newsletter_subscribers:
                    all_recipients.add(subscriber.email)
                
                # Récupérer tous les utilisateurs actifs
                users = g.db.query(User).filter_by(is_active=True).all()
                for user in users:
                    if user.email:  # Vérifier que l'email existe
                        all_recipients.add(user.email)
            else:
                if not selected_subscribers:
                    return jsonify({'success': False, 'message': 'Aucun destinataire sélectionné'})
                
                # Récupérer les abonnés sélectionnés
                selected = g.db.query(NewsletterSubscriber).filter(
                    NewsletterSubscriber.id.in_(selected_subscribers),
                    NewsletterSubscriber.status=='active'
                ).all()
                for subscriber in selected:
                    all_recipients.add(subscriber.email)

            if not all_recipients:
                if not admin_email:
                    return jsonify({'success': False, 'message': 'Aucun destinataire actif trouvé et email administrateur non configuré'})
                msg = Message(
                    subject=subject,
                    recipients=[admin_email],
                    html=html_content + '<p><em>Note: Cette newsletter a été envoyée uniquement à l\'administrateur car aucun abonné actif n\'a été trouvé.</em></p>'
                )
                current_app.extensions['mail'].send(msg)
                recipient_count = 1
                message = 'Newsletter envoyée uniquement à l\'administrateur (aucun abonné actif)'
            else:
                success_count = 0
                error_count = 0
                for email in all_recipients:
                    try:
                        msg = Message(
                            subject=subject,
                            recipients=[email],
                            html=html_content
                        )
                        current_app.extensions['mail'].send(msg)
                        
                        # Mettre à jour la date de dernière newsletter pour les abonnés
                        subscriber = g.db.query(NewsletterSubscriber).filter_by(email=email).first()
                        if subscriber:
                            subscriber.last_newsletter = datetime.now()
                            g.db.commit()
                        
                        success_count += 1
                    except Exception as e:
                        print(f"Erreur lors de l'envoi à {email}: {str(e)}")
                        error_count += 1
                        continue
                
                recipient_count = success_count
                message = f'Newsletter envoyée à {success_count} destinataire(s)'
                if error_count > 0:
                    message += f' ({error_count} échec(s))'
        
        # Enregistrer l'historique
        nh = NewsletterHistory(
            subject=subject,
            content=html_content,
            sent_by=current_user.id,
            recipient_count=recipient_count,
            test_send=test_send
        )
        g.db.add(nh)
        g.db.commit()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        print(f"Erreur lors de l'envoi de la newsletter: {str(e)}")
        g.db.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/admin/newsletter/<int:newsletter_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_newsletter(newsletter_id):
    newsletter = g.db.query(NewsletterHistory).filter_by(id=newsletter_id).first_or_404()
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        article_ids = request.form.getlist('articles')
        
        if not subject or not content:
            flash('Le sujet et le contenu sont requis.', 'error')
            return redirect(url_for('admin.edit_newsletter', newsletter_id=newsletter_id))
        
        try:
            newsletter.subject = subject
            newsletter.content = content
            newsletter.article_ids = ','.join(map(str, article_ids))
            newsletter.updated_at = datetime.now()
            g.db.commit()
            
            flash('Newsletter modifiée avec succès !', 'success')
            return redirect(url_for('admin.manage_newsletter'))
        except Exception as e:
            g.db.rollback()
            flash('Erreur lors de la modification de la newsletter.', 'error')
            print(f"Erreur lors de la modification de la newsletter : {e}")
            return redirect(url_for('admin.edit_newsletter', newsletter_id=newsletter_id))
    
    # Récupérer tous les articles pour le formulaire
    articles = g.db.query(Article).order_by(Article.created_at.desc()).all()
    
    # Convertir les IDs d'articles en liste
    selected_articles = newsletter.article_ids.split(',') if newsletter.article_ids else []
    
    return render_template('admin/edit_newsletter.html', 
                         newsletter=newsletter, 
                         articles=articles,
                         selected_articles=selected_articles)

@admin_bp.route('/admin/newsletter/<int:newsletter_id>/content')
@login_required
@admin_required
def get_newsletter_content(newsletter_id):
    try:
        newsletter = g.db.query(NewsletterHistory).filter_by(id=newsletter_id).first()
        
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
    return g.db.query(NewsletterHistory).order_by(NewsletterHistory.sent_at.desc()).all()

def get_newsletter_by_id(newsletter_id):
    return g.db.query(NewsletterHistory).filter_by(id=newsletter_id).first()

def create_newsletter(subject, content, sent_by, recipient_count=0, test_send=False):
    newsletter = NewsletterHistory(
        subject=subject,
        content=content,
        sent_by=sent_by,
        recipient_count=recipient_count,
        test_send=test_send,
        sent_at=datetime.now()
    )
    g.db.add(newsletter)
    g.db.commit()
    return newsletter

def update_newsletter(newsletter_id, subject, content, article_ids=None):
    newsletter = g.db.query(NewsletterHistory).filter_by(id=newsletter_id).first()
    if newsletter:
        newsletter.subject = subject
        newsletter.content = content
        if article_ids is not None:
            newsletter.article_ids = ','.join(map(str, article_ids))
        newsletter.updated_at = datetime.now()
        g.db.commit()
        return True
    return False

def delete_newsletter(newsletter_id):
    newsletter = g.db.query(NewsletterHistory).filter_by(id=newsletter_id).first()
    if newsletter:
        g.db.delete(newsletter)
        g.db.commit()
        return True
    return False

# Mise à jour de la route d'import des abonnés
@admin_bp.route('/admin/newsletter/import', methods=['POST'])
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
                existing = g.db.query(NewsletterSubscriber).filter_by(email=row['email']).first()
                if not existing:
                    subscriber = NewsletterSubscriber(
                        email=row['email'],
                        status='active',
                        subscribed_at=datetime.now()
                    )
                    g.db.add(subscriber)
                    count += 1

        g.db.commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'message': str(e)})



# Mise à jour de la route d'export des abonnés
@admin_bp.route('/admin/newsletter/export')
@login_required
@admin_required
def export_subscribers():
    try:
        # Créer un fichier CSV en mémoire
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['email', 'status', 'subscribed_at', 'last_newsletter'])

        subscribers = g.db.query(NewsletterSubscriber).all()
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

@admin_bp.route('/admin/newsletter/subscribers/<int:subscriber_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subscriber(subscriber_id):
    subscriber = g.db.query(NewsletterSubscriber).filter_by(id=subscriber_id).first()
    if not subscriber:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    try:
        g.db.delete(subscriber)
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/admin/newsletter/subscribers/<int:subscriber_id>/<action>', methods=['POST'])
@login_required
@admin_required
def toggle_subscriber_status(subscriber_id, action):
    if action not in ['unsubscribe', 'resubscribe']:
        return jsonify({'success': False, 'message': 'Action invalide'})
    subscriber = g.db.query(NewsletterSubscriber).filter_by(id=subscriber_id).first()
    if not subscriber:
        return jsonify({'success': False, 'message': 'Abonné non trouvé'})
    try:
        if action == 'unsubscribe':
            subscriber.status = 'unsubscribed'
        else:
            subscriber.status = 'active'
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'message': str(e)})



class AdminVerifyForm(FlaskForm):
    code = StringField('Code de vérification', validators=[DataRequired()])

@admin_bp.route('/admin/verify', methods=['GET'])
def admin_verify():
    if not session.get('admin_email'):
        return redirect(url_for('main.login'))
    form = AdminVerifyForm()
    return render_template('admin_verify.html', form=form)

@admin_bp.route('/admin/verify-code', methods=['POST'])
def verify_admin_code():
    if not session.get('admin_email'):
        return redirect(url_for('main.login'))
    
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
                    user = g.db.query(User).filter_by(email=session['admin_email']).first()
                    
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
                        g.db.add(user)
                        g.db.commit()
                        login_user(user)
                    
                    session.pop('admin_code', None)
                    session.pop('admin_code_expiry', None)
                    session.pop('admin_email', None)
                    flash('Vérification réussie !', 'success')
                    return redirect(url_for('admin.admin_dashboard'))
                else:
                    flash('Code invalide', 'error')
            else:
                flash('Code expiré', 'error')
                # Générer un nouveau code
                session_code = generate_session_code()
                session['admin_code'] = session_code
                session['admin_code_expiry'] = datetime.now().replace(tzinfo=None) + timedelta(minutes=15)
                
                if send_admin_code(
                    admin_email=session['admin_email'],
                    admin_name="Administrateur",
                    admin_code=session_code
                ):
                    flash('Un nouveau code a été envoyé à votre email', 'info')
                else:
                    flash('Erreur lors de l\'envoi du code. Veuillez réessayer.', 'error')
        else:
            flash('Session invalide ou expirée', 'error')
        
    return redirect(url_for('admin.admin_verify'))


@admin_bp.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    # Statistiques générales
    total_views = g.db.query(PageView).count()
    unique_visitors = g.db.query(PageView.ip_address.distinct()).count()
    
    # Visites aujourd'hui
    today = datetime.utcnow().date()
    today_views = g.db.query(PageView).filter(
        func.date(PageView.viewed_at) == today
    ).count()
    
    # Visites cette semaine
    week_start = today - timedelta(days=today.weekday())
    week_views = g.db.query(PageView).filter(
        func.date(PageView.viewed_at) >= week_start,
        func.date(PageView.viewed_at) < today
    ).count()
    
    # Statistiques par page
    page_stats = g.db.query(
        PageView.page,
        func.count(PageView.id).label('views')
    ).group_by(PageView.page).all()
    
    # Statistiques des 7 derniers jours
    last_week = datetime.utcnow() - timedelta(days=7)
    daily_stats = g.db.query(
        func.date(PageView.viewed_at).label('date'),
        func.count(PageView.id).label('views')
    ).filter(
        PageView.viewed_at >= last_week,
        PageView.viewed_at < datetime.utcnow()
    ).group_by(
        func.date(PageView.viewed_at)
    ).all()
    
    # Statistiques des navigateurs
    browser_stats = g.db.query(
        func.substring(PageView.user_agent, 1, 50).label('browser'),
        func.count(PageView.id).label('count')
    ).group_by(
        func.substring(PageView.user_agent, 1, 50)
    ).all()
    
    # Statistiques des sources de trafic
    referrer_stats = g.db.query(
        func.coalesce(PageView.referrer, 'Direct').label('source'),
        func.count(PageView.id).label('count')
    ).group_by(
        func.coalesce(PageView.referrer, 'Direct')
    ).all()
    
    # Articles les plus vus
    top_articles = g.db.query(
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
    top_categories = g.db.query(
        Category,
        func.count(PageView.id).label('views')
    ).outerjoin(
        PageView,
        and_(
            or_(
                and_(PageView.page == 'category', PageView.page_id == Category.id),
                and_(PageView.page == 'article', PageView.page_id.in_(
                    g.db.query(Article.id).filter(Article.category_id == Category.id)
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

@admin_bp.route('/get-csrf-token')
def get_csrf_token():
    """Route pour obtenir un nouveau token CSRF"""
    return jsonify({'csrf_token': generate_csrf()})
