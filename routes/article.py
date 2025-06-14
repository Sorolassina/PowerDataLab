from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, jsonify
from models.article import Article
from models.category import Category
from models.user import User
from models.page_view import PageView
from datetime import datetime
from flask_login import current_user
from sqlalchemy import func
import os
from models.comment import Comment
from flask_wtf import FlaskForm
from flask import request, render_template, redirect, url_for, flash
from models.article import Article
from models.category import Category
from models.user import User
from models.page_view import PageView
from datetime import datetime
from utils.verif_image import clean_duplicate_images
from utils.decorateur import login_required, admin_required
from flask import current_app
from utils.verif_image import allowed_file
from werkzeug.utils import secure_filename
from slugify import slugify
from models.base import SessionLocal
from models.article_document import ArticleDocument

article_bp = Blueprint('article', __name__)

def allowed_document(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def fix_document_paths():
    """Corrige les chemins des documents en remplaçant les backslashes par des slashes"""
    documents = g.db.query(ArticleDocument).all()
    for doc in documents:
        if '\\' in doc.file_path:
            # Remplacer tous les backslashes par des slashes
            doc.file_path = doc.file_path.replace('\\', '/')
    g.db.commit()

@article_bp.route('/admin/fix-document-paths', methods=['POST'])
@admin_required
def run_fix_document_paths():
    try:
        fix_document_paths()
        return jsonify({'success': True, 'message': 'Chemins des documents corrigés avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def save_document(file, article_id):
    if file and allowed_document(file.filename):
        filename = secure_filename(file.filename)
        # Générer un nom unique pour éviter les conflits
        base, ext = os.path.splitext(filename)
        unique_filename = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        
        # Utiliser le dossier uploads
        upload_folder = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Sauvegarder le fichier
        # Utiliser des slashes pour le chemin stocké en base de données
        file_path = 'uploads/' + unique_filename
        # Utiliser os.path.join pour le chemin système réel
        full_path = os.path.join(current_app.static_folder, 'uploads', unique_filename)
        file.save(full_path)
        
        # Créer l'entrée dans la base de données
        document = ArticleDocument(
            article_id=article_id,
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(full_path),
            file_type=ext[1:]  # Enlever le point du début de l'extension
        )
        
        return document
    return None

@article_bp.route('/article/<slug>')
def article(slug):
    # Récupérer l'article avec toutes ses relations
    article_query = g.db.query(
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
        return redirect(url_for('main.index'))

    # Récupérer les documents de l'article
    documents = g.db.query(ArticleDocument).filter_by(article_id=article_query.Article.id).all()

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
        'author_name': article_query.author_name,
        'documents': documents  # Ajout des documents
    }

    # Récupérer les commentaires avec les informations de l'auteur
    comments_query = g.db.query(
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
    g.db.add(page_view)
    g.db.commit()

    return render_template('article.html', article=article_dict, comments=comments)

@article_bp.route('/admin/articles')
@login_required
@admin_required
def manage_articles():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Calculer le nombre total d'articles
    total = g.db.query(Article).count()
    
    # Calculer l'offset pour la pagination
    offset = (page - 1) * per_page

    # Récupérer les articles avec leurs catégories
    articles_query = g.db.query(
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

@article_bp.route('/admin/articles/new', methods=['GET', 'POST'])
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
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
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
            g.db.add(article)
            g.db.flush()  # Pour obtenir l'ID de l'article
            
            # Gérer l'upload des documents
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                for file in files:
                    document = save_document(file, article.id)
                    if document:
                        g.db.add(document)
            
            g.db.commit()
            
            # Nettoyer les images en double
            clean_duplicate_images()
            
            flash('Article créé avec succès !', 'success')
            return redirect(url_for('article.manage_articles'))
        except Exception as e:
            g.db.rollback()
            flash('Erreur lors de la création de l\'article.', 'error')
            print(f"Erreur lors de la création de l'article : {e}")
    
    categories = g.db.query(Category).order_by(Category.name).all()
    return render_template('admin/article_form.html', categories=categories)

@article_bp.route('/admin/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_article(article_id):
    article = g.db.query(Article).filter_by(id=article_id).first()
    
    if request.method == 'POST':
        print(f"[DEBUG] Début de l'édition de l'article {article_id}")
        article.title = request.form['title']
        article.content = request.form['content']
        article.category_id = request.form['category_id']
        article.slug = slugify(article.title)
        
        # Gestion des images existantes et nouvelles
        existing_images = request.form.getlist('existing_images')
        print(f"[DEBUG] Images existantes : {existing_images}")
        image_paths = [img.replace('\\', '/') for img in existing_images if img]
        
        if 'images' in request.files:
            files = request.files.getlist('images')
            print(f"[DEBUG] Nombre de nouvelles images : {len(files)}")
            for file in files:
                if file and file.filename:
                    print(f"[DEBUG] Traitement de l'image : {file.filename}")
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                        print(f"[DEBUG] Chemin de sauvegarde : {file_path}")
                        try:
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            file.save(file_path)
                            print(f"[DEBUG] Fichier sauvegardé avec succès")
                            rel_path = os.path.join('uploads', filename).replace('\\', '/')
                            image_paths.append(rel_path)
                        except Exception as e:
                            print(f"[DEBUG] Erreur lors de la sauvegarde : {str(e)}")
                    else:
                        print(f"[DEBUG] Type de fichier non autorisé : {file.filename}")
        
        # Nettoyer la liste (supprimer les vides)
        image_paths = [p for p in image_paths if p]
        print(f"[DEBUG] Chemins d'images finaux : {image_paths}")
        article.image_path = ','.join(image_paths) if image_paths else None
        
        # Gérer l'upload des documents
        if 'documents' in request.files:
            files = request.files.getlist('documents')
            for file in files:
                document = save_document(file, article.id)
                if document:
                    g.db.add(document)
        
        article.updated_at = datetime.now()
        g.db.commit()
        
        # Nettoyer les images en double
        clean_duplicate_images()
        
        flash('Article modifié avec succès !', 'success')
        return redirect(url_for('article.manage_articles'))
    
    categories = g.db.query(Category).order_by(Category.name).all()
    return render_template('admin/article_form.html', article=article, categories=categories)

@article_bp.route('/admin/articles/delete/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def delete_article_route(article_id):
    article = g.db.query(Article).filter_by(id=article_id).first()
    if article is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('article.manage_articles'))
    
    try:
        # Supprimer l'image si elle existe
        if article.image_path:
            try:
                for image_path in article.image_path.split(','):
                    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(image_path))
                    if os.path.exists(full_path):
                        os.remove(full_path)
            except Exception as e:
                print(f"Erreur lors de la suppression de l'image : {e}")
        
        # Supprimer l'article
        g.db.delete(article)
        g.db.commit()
        
        flash('Article supprimé avec succès!', 'success')
    except Exception as e:
        g.db.rollback()
        flash('Erreur lors de la suppression de l\'article.', 'error')
        print(f"Erreur lors de la suppression de l'article : {e}")
    
    return redirect(url_for('article.manage_articles'))

@article_bp.route('/admin/article/document/<int:id>/delete', methods=['POST'])
@admin_required
def delete_document(id):
    document = g.db.query(ArticleDocument).get_or_404(id)
    
    # Supprimer le fichier physique
    file_path = os.path.join(current_app.static_folder, document.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Supprimer l'entrée de la base de données
    g.db.delete(document)
    g.db.commit()
    
    return jsonify({'success': True})