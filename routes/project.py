# Dans routes/project.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, send_from_directory, session, jsonify
from models.project import Project
from models.category import Category
from models.project_document import ProjectDocument
from schema_pydantic.schemas_pda import ProjectForm
from utils.decorateur import admin_required, login_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask import jsonify
import mimetypes
from flask_login import current_user
from flask_wtf import FlaskForm
from routes.uploads import save_file, save_files, delete_file

project_bp = Blueprint('project', __name__)

class DeleteForm(FlaskForm):
    pass

# Liste des projets
@project_bp.route('/projects')
def projects():
    projects = g.db.query(Project).all()
    categories = g.db.query(Category).all()
    form = DeleteForm()
    
    # Créer un dictionnaire pour mapper les noms de catégories aux slugs
    category_slug_map = {cat.name: cat.slug for cat in categories}
    
    # Ajouter le slug de catégorie à chaque projet
    for project in projects:
        project.category_slug = category_slug_map.get(project.category, project.category.lower().replace(' ', '-'))
    
    return render_template('projects.html', projects=projects, categories=categories, form=form)

# Créer un nouveau projet
@project_bp.route('/admin/projects/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_project():
    form = ProjectForm()
    # Charger les catégories depuis la base de données
    categories = g.db.query(Category).all()
    form.category.choices = [(cat.slug, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        try:
            # Gestion de l'image
            image_path = None
            if form.image.data:
                image_path = save_file(form.image.data, 'image')

            # Gestion de la vidéo
            video_path = None
            if 'video' in request.files and request.files['video'].filename:
                video_file = request.files['video']
                if video_file and video_file.filename:
                    # Vérifier la taille du fichier (100MB max)
                    video_file.seek(0, 2)  # Aller à la fin du fichier
                    file_size = video_file.tell()
                    video_file.seek(0)  # Retourner au début
                    
                    if file_size > 500 * 1024 * 1024:  # 500MB
                        flash('La vidéo est trop volumineuse. Taille maximale autorisée : 500 MB', 'error')
                        return render_template('admin/project_form.html', form=form)
                    
                    video_path = save_file(video_file, 'video')

            # Création du projet
            project = Project(
                title=form.title.data,
                description=form.description.data,
                category=form.category.data,
                category_color=form.category_color.data or 'primary',
                image_path=image_path,
                video_path=video_path,
                demo_url=form.demo_url.data,
                github_url=form.github_url.data,
                technologies=form.technologies.data,
                is_featured=form.is_featured.data,
                status=form.status.data
            )
            g.db.add(project)
            g.db.flush()

            # Gestion des documents
            if form.documents.data:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        file_path = save_file(file, 'document')
                        if file_path:
                            # Créer l'entrée dans la base de données
                            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(file_path))
                            document = ProjectDocument(
                                project_id=project.id,
                                filename=os.path.basename(file_path),
                                original_filename=file.filename,
                                file_path=file_path,
                                file_size=os.path.getsize(full_path),
                                file_type=mimetypes.guess_type(file.filename)[0]
                            )
                            g.db.add(document)

            g.db.commit()
            flash('Projet créé avec succès !', 'success')
            return redirect(url_for('project.projects'))
        except Exception as e:
            g.db.rollback()
            flash('Erreur lors de la création du projet.', 'error')
            print(f"Erreur lors de la création du projet : {e}")
    
    return render_template('admin/project_form.html', form=form)

# Modifier un projet existant
@project_bp.route('/admin/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_project(project_id):
    project = g.db.query(Project).filter(Project.id == project_id).first()
    if not project:
        flash('Projet non trouvé.', 'error')
        return redirect(url_for('project.projects'))
        
    form = ProjectForm(obj=project)
    
    # Charger les catégories depuis la base de données
    categories = g.db.query(Category).all()
    form.category.choices = [(cat.slug, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        try:
            # Gestion de l'image
            if form.image.data:
                # Supprimer l'ancienne image si elle existe
                if project.image_path:
                    delete_file(os.path.basename(project.image_path))
                # Sauvegarder la nouvelle image
                project.image_path = save_file(form.image.data, 'image')

            # Gestion de la vidéo
            if 'video' in request.files and request.files['video'].filename:
                video_file = request.files['video']
                if video_file and video_file.filename:
                    # Vérifier la taille du fichier (100MB max)
                    video_file.seek(0, 2)  # Aller à la fin du fichier
                    file_size = video_file.tell()
                    video_file.seek(0)  # Retourner au début
                    
                    if file_size > 500 * 1024 * 1024:  # 500MB
                        flash('La vidéo est trop volumineuse. Taille maximale autorisée : 500 MB', 'error')
                        return render_template('admin/project_form.html', form=form, project=project)
                    
                    # Supprimer l'ancienne vidéo si elle existe
                    if project.video_path:
                        delete_file(os.path.basename(project.video_path))
                    # Sauvegarder la nouvelle vidéo
                    project.video_path = save_file(video_file, 'video')

            # Mise à jour des autres champs
            project.title = form.title.data
            project.description = form.description.data
            project.category = form.category.data
            project.category_color = form.category_color.data or 'primary'
            project.demo_url = form.demo_url.data
            project.github_url = form.github_url.data
            project.technologies = form.technologies.data
            project.is_featured = form.is_featured.data
            project.status = form.status.data

            # Gestion des nouveaux documents
            if form.documents.data:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        file_path = save_file(file, 'document')
                        if file_path:
                            # Créer l'entrée dans la base de données
                            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(file_path))
                            document = ProjectDocument(
                                project_id=project.id,
                                filename=os.path.basename(file_path),
                                original_filename=file.filename,
                                file_path=file_path,
                                file_size=os.path.getsize(full_path),
                                file_type=mimetypes.guess_type(file.filename)[0]
                            )
                            g.db.add(document)

            g.db.commit()
            flash('Projet modifié avec succès !', 'success')
            return redirect(url_for('project.projects'))
        except Exception as e:
            g.db.rollback()
            flash('Erreur lors de la modification du projet.', 'error')
            print(f"Erreur lors de la modification du projet : {e}")
    
    return render_template('admin/project_form.html', form=form, project=project)

@project_bp.route('/project/delete/<int:project_id>', methods=['POST'])
@admin_required
def delete_project(project_id):
    project = g.db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        flash('Projet non trouvé.', 'danger')
        return redirect(url_for('project.projects'))
    
    try:
        # Supprimer l'image si elle existe
        if project.image_path:
            delete_file(os.path.basename(project.image_path))
        
        # Supprimer les documents associés
        for document in project.documents:
            delete_file(os.path.basename(document.file_path))
        
        # Supprimer le projet de la base de données
        g.db.delete(project)
        g.db.commit()
        flash('Projet supprimé avec succès.', 'success')
    except Exception as e:
        g.db.rollback()
        flash('Erreur lors de la suppression du projet.', 'danger')
        print(f"Erreur lors de la suppression du projet : {e}")
    
    return redirect(url_for('project.projects'))

# Incrémenter les vues d'un projet
@project_bp.route('/projects/<int:project_id>/view', methods=['POST'])
def increment_views(project_id):
    project = g.db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return jsonify({'error': 'Projet non trouvé'}), 404
        
    project.views += 1
    g.db.commit()
    return jsonify({'views': project.views})

# Ajouter/Retirer un like
@project_bp.route('/projects/<int:project_id>/like', methods=['POST'])
def toggle_like(project_id):
    # Vérifier le token CSRF
    csrf_token = request.form.get('csrf_token')
    if not csrf_token:
        return jsonify({'error': 'Token CSRF manquant'}), 400
        
    project = g.db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return jsonify({'error': 'Projet non trouvé'}), 404
        
    project.likes += 1
    g.db.commit()
    return jsonify({'likes': project.likes})

# Télécharger un document
@project_bp.route('/projects/documents/<int:document_id>/download')
def download_document(document_id):
    document = g.db.query(ProjectDocument).filter(ProjectDocument.id == document_id).first()
    if not document:
        flash('Document non trouvé.', 'error')
        return redirect(url_for('project.projects'))
        
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        document.filename,
        as_attachment=True,
        download_name=document.original_filename
    )

# Supprimer un document
@project_bp.route('/admin/projects/documents/<int:document_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_document(document_id):
    # Vérifier le token CSRF
    csrf_token = request.headers.get('X-CSRFToken')
    if not csrf_token:
        return jsonify({
            'success': False,
            'error': 'Token CSRF manquant'
        }), 403

    document = g.db.query(ProjectDocument).get(document_id)
    if not document:
        return jsonify({
            'success': False,
            'error': f"Le document avec l'ID {document_id} n'existe pas"
        }), 404

    try:
        # Essayer de supprimer le fichier physique
        file_deleted = delete_file(os.path.basename(document.file_path))
        
        # Supprimer l'entrée de la base de données, que le fichier physique existe ou non
        g.db.delete(document)
        g.db.commit()
        
        message = f'Le document "{document.original_filename}" a été supprimé avec succès'
        if not file_deleted:
            message += ' (le fichier physique était déjà absent)'
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        g.db.rollback()
        print(f"Erreur lors de la suppression du document {document_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Une erreur est survenue lors de la suppression du document: {str(e)}"
        }), 500