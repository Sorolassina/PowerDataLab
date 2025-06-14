from flask_login import login_manager,current_user
from models.user import User
from models.base import SessionLocal
from werkzeug.security import generate_password_hash
from flask import request, render_template, redirect, url_for, flash, Blueprint, g, current_app, jsonify
from models.article import Article
from models.comment import Comment
from sqlalchemy import func 
from utils.decorateur import admin_required,login_required

user_bp = Blueprint('user', __name__)

# Fonctions de gestion des utilisateurs
def get_user_by_id(user_id):
    return g.db.query(User).filter_by(id=user_id).first()

def get_user_by_email(email):
    return g.db.query(User).filter_by(email=email).first()

def create_user(username, email, password, is_admin=False):
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
        is_blocked=False
    )
    g.db.add(user)
    g.db.commit()
    return user

def update_user(user_id, **kwargs):
    user = g.db.query(User).filter_by(id=user_id).first()
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        g.db.commit()
        return True
    return False

def delete_user(user_id):
    user = g.db.query(User).filter_by(id=user_id).first()
    if user:
        g.db.delete(user)
        g.db.commit()
        return True
    return False

@user_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Compter le nombre total d'utilisateurs
    total = g.db.query(User).count()
    
    # Récupérer les utilisateurs avec pagination et leurs statistiques
    users_query = g.db.query(
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

@user_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Vous ne pouvez pas supprimer votre propre compte.'
        })
    
    user = g.db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Utilisateur non trouvé.'
        })
    
    try:
        # Supprimer d'abord les articles et commentaires de l'utilisateur
        g.db.query(Article).filter_by(author_id=user_id).delete()
        g.db.query(Comment).filter_by(user_id=user_id).delete()
        
        # Puis supprimer l'utilisateur
        g.db.delete(user)
        g.db.commit()
        return jsonify({
            'success': True,
            'message': 'Utilisateur supprimé avec succès !'
        })
    except Exception as e:
        g.db.rollback()
        print(f"Erreur lors de la suppression de l'utilisateur : {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la suppression de l\'utilisateur.'
        })

@user_bp.route('/admin/users/<int:user_id>/toggle-block', methods=['POST'])
@login_required
@admin_required
def toggle_user_block(user_id):
    if user_id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Vous ne pouvez pas bloquer votre propre compte.'
        })
    
    user = g.db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Utilisateur non trouvé.'
        })
    
    try:
        user.is_blocked = not user.is_blocked
        g.db.commit()
        
        status = 'débloqué' if not user.is_blocked else 'bloqué'
        return jsonify({
            'success': True,
            'message': f'L\'utilisateur a été {status}.'
        })
    except Exception as e:
        g.db.rollback()
        print(f"Erreur lors de la modification du statut de l'utilisateur : {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la modification du statut de l\'utilisateur.'
        })