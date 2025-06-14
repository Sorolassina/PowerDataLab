from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from models.comment import Comment
from models.user import User
from models.article import Article
from models.base import SessionLocal
from utils.decorateur import admin_required, login_required
from sqlalchemy import func
from flask_login import current_user
from sqlalchemy import text
from models.base import engine

comment_bp = Blueprint('comment', __name__)

@comment_bp.route('/comments')
@login_required
@admin_required
def manage_comments():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    total = g.db.query(Comment).count()
    
    # Récupérer les commentaires avec leurs relations
    comments_query = g.db.query(
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

@comment_bp.route('/admin/comments/delete/<int:comment_id>', methods=['POST'])
@login_required
@admin_required
def delete_comment_route(comment_id):
    comment = g.db.query(Comment).filter_by(id=comment_id).first()
    if comment is None:
        flash('Commentaire non trouvé.', 'error')
        return redirect(url_for('admin.manage_comments'))
    try:
        g.db.delete(comment)
        g.db.commit()
        flash('Commentaire supprimé avec succès!', 'success')
    except Exception as e:
        g.db.rollback()
        flash('Erreur lors de la suppression du commentaire.', 'error')
        print(f"Erreur lors de la suppression du commentaire : {e}")
    return redirect(url_for('admin.manage_comments'))

@comment_bp.route('/article/<slug>/comment', methods=['POST'])
@login_required
def add_comment(slug):
    article = g.db.query(Article).filter_by(slug=slug).first()
    if article is None:
        flash('Article non trouvé.', 'error')
        return redirect(url_for('main.index'))
    content = request.form.get('content')
    if not content:
        flash('Le contenu du commentaire est requis.', 'error')
        return redirect(url_for('article.article', slug=slug))
    comment = Comment(
        content=content,
        article_id=article.id,
        user_id=current_user.id
    )
    g.db.add(comment)
    g.db.commit()
    flash('Commentaire ajouté avec succès!', 'success')
    return redirect(url_for('article.article', slug=slug))

@comment_bp.route('/admin/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_comment(comment_id):
    comment = g.db.query(Comment).filter_by(id=comment_id).first()
    if not comment:
        flash('Commentaire non trouvé.', 'error')
        return redirect(url_for('admin.manage_comments'))
    
    try:
        # Si l'attribut is_approved n'existe pas, on l'ajoute
        if not hasattr(Comment, 'is_approved'):
            # Ajouter la colonne is_approved à la table Comment
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE comment ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE'))
                conn.commit()
        
        # Inverser le statut d'approbation
        comment.is_approved = not comment.is_approved
        g.db.commit()
        
        status = 'approuvé' if comment.is_approved else 'désapprouvé'
        flash(f'Le commentaire a été {status}.', 'success')
    except Exception as e:
        g.db.rollback()
        flash('Erreur lors de la modification du statut du commentaire.', 'error')
        print(f"Erreur lors de la modification du statut du commentaire : {e}")
    
    return redirect(url_for('admin.manage_comments'))
