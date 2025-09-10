from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, jsonify
from models.category import Category
from models.article import Article
from models.page_view import PageView
from datetime import datetime
from flask_login import current_user
from flask_mail import Message
import os
from slugify import slugify
from models.base import SessionLocal  # Import ajouté
from markupsafe import Markup
import re
from bs4 import BeautifulSoup
from utils.decorateur import login_required, admin_required
from schema_pydantic.schemas_pda import NewsletterForm


category_bp = Blueprint('category', __name__)

def clean(html_content, strip=False):
    """Fonction pour nettoyer le contenu HTML"""
    if not html_content:
        return ""
    
    # Utiliser BeautifulSoup pour nettoyer le HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if strip:
        # Supprimer toutes les balises HTML et retourner le texte brut
        return soup.get_text()
    else:
        # Retourner le HTML nettoyé
        return str(soup)

@category_bp.route('/category/<slug>')
def category(slug):
    category = g.db.query(Category).filter_by(slug=slug).first()
    if category is None:
        flash('Catégorie non trouvée.', 'error')
        return redirect(url_for('index'))
        
    articles = g.db.query(Article).filter_by(category_id=category.id).order_by(Article.created_at.desc()).all()
    
    # Créer des excerpts pour les articles
    articles_with_excerpts = []
    import re
    from bs4 import BeautifulSoup
    
    for article in articles:
        # Nettoyer le HTML et créer un excerpt
        clean_content = clean(article.content, strip=True)
        
        # Supprimer les balises HTML pour compter les caractères
        text_only = re.sub(r'<[^>]+>', '', clean_content)
        text_only = re.sub(r'\s+', ' ', text_only).strip()
        
        # Si le texte est plus long que 200 caractères, tronquer et ajouter ...
        if len(text_only) > 200:
            truncated_text = text_only[:200]
            last_space = truncated_text.rfind(' ')
            if last_space > 150:
                truncated_text = truncated_text[:last_space]
            excerpt = truncated_text + '...'
        else:
            excerpt = text_only
        
        # Ajouter l'excerpt à l'objet article
        article.excerpt = excerpt
        # S'assurer que video_path est accessible
        article.video_path = article.video_path
        articles_with_excerpts.append(article)
    
    # Charger toutes les catégories avec leur nombre d'articles
    categories = g.db.query(Category).all()
    for cat in categories:
        cat.article_count = g.db.query(Article).filter_by(category_id=cat.id).count()
        print(f"[DEBUG] Catégorie {cat.name}: color_theme = {cat.color_theme}")
    
    # Formulaire newsletter
    newsletter_form = NewsletterForm()
    
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
    g.db.add(page_view)
    g.db.commit()
    
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
            current_app.mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de la notification : {e}")
    
    return render_template('category.html', 
                         category=category, 
                         articles=articles_with_excerpts, 
                         categories=categories,
                         newsletter_form=newsletter_form)

@category_bp.route('/admin/update-categories')
@login_required
@admin_required
def update_categories():
    try:
    # Supprimer toutes les catégories existantes
        g.db.query(Category).delete()
    
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
            g.db.add(category)
            
            g.db.commit()
            flash('Catégories mises à jour avec succès !', 'success')
    except Exception as e:
        g.db.rollback()
        flash('Erreur lors de la mise à jour des catégories.', 'error')
        print(f"Erreur: {e}")
    
    return redirect(url_for('admin'))

@category_bp.route('/admin/categories')
@login_required
@admin_required
def manage_categories():
    categories = g.db.query(Category).all()
    return render_template('admin/manage_categories.html', categories=categories)

@category_bp.route('/admin/categories/new', methods=['GET', 'POST'])
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
                return redirect(url_for('category.manage_categories'))
            
            try:
                slug = slugify(name)
                category = Category(
                    name=name,
                    slug=slug,
                    color_theme=color_theme,
                    description=description
                )
                g.db.add(category)
                g.db.commit()
                
                flash('Catégorie créée avec succès', 'success')
                return redirect(url_for('category.manage_categories'))
            except Exception as e:
                g.db.rollback()
                print(f"Erreur lors de la création: {str(e)}")
                flash('Erreur lors de la création de la catégorie', 'error')
                return redirect(url_for('category.manage_categories'))
                
        except Exception as e:
            print(f"Erreur lors du traitement POST: {str(e)}")
            flash('Erreur lors de la création de la catégorie', 'error')
            return redirect(url_for('category.manage_categories'))
    
    # Pour les requêtes GET, on affiche simplement le formulaire
    return render_template('admin/manage_categories.html')

@category_bp.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
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
                return redirect(url_for('category.manage_categories'))
            
            category = g.db.query(Category).filter_by(id=category_id).first()
            if category is None:
                flash('Catégorie non trouvée', 'error')
                return redirect(url_for('category.manage_categories'))
            
            try:
                category.name = name
                category.slug = slugify(name)
                category.color_theme = color_theme
                category.description = description
                g.db.commit()
                
                flash('Catégorie mise à jour avec succès', 'success')
                return redirect(url_for('category.manage_categories'))
            except Exception as e:
                g.db.rollback()
                print(f"Erreur lors de la mise à jour: {str(e)}")
                flash('Erreur lors de la mise à jour de la catégorie', 'error')
                return redirect(url_for('category.manage_categories'))
                
        except Exception as e:
            g.db.rollback()
            print(f"Erreur lors de la mise à jour: {str(e)}")
            flash('Erreur lors de la mise à jour de la catégorie', 'error')
            return redirect(url_for('category.manage_categories'))
    
    # Pour les requêtes GET, on récupère la catégorie
    category = g.db.query(Category).get(category_id)
    if not category:
        flash('Catégorie non trouvée.', 'error')
        return redirect(url_for('category.manage_categories'))
    
    # Vérifier si la requête demande du JSON (pour l'API)
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'id': category.id,
            'name': category.name,
            'color': category.color_theme,
            'description': category.description or '',
            'slug': category.slug
        })
    
    # Vérifier si la catégorie a des articles associés
    has_articles = g.db.query(Article).filter_by(category_id=category_id).first() is not None
    
    return render_template('admin/manage_categories.html', 
                         category=category, 
                         is_edit=True,
                         has_articles=has_articles)

@category_bp.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category_route(category_id):
    try:
        category = g.db.query(Category).get(category_id)
        if not category:
            flash('Catégorie non trouvée.', 'error')
            return redirect(url_for('category.manage_categories'))
        
        # Vérifier si la catégorie a des articles associés
        if category.articles:
            flash('Impossible de supprimer une catégorie qui contient des articles.', 'error')
            return redirect(url_for('category.manage_categories'))
        
        g.db.delete(category)
        g.db.commit()
        flash('Catégorie supprimée avec succès.', 'success')
    except Exception as e:
        g.db.rollback()
        flash(f'Erreur lors de la suppression de la catégorie: {str(e)}', 'error')
    
    return redirect(url_for('category.manage_categories'))
