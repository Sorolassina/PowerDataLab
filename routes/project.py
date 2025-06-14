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

project_bp = Blueprint('project', __name__)

class DeleteForm(FlaskForm):
    pass

# Liste des projets
@project_bp.route('/projects')
def projects():
    projects = g.db.query(Project).all()
    categories = g.db.query(Category).all()
    form = DeleteForm()
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
                file = form.image.data
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    image_path = os.path.join('uploads', filename).replace('\\', '/')

            # Création du projet
            project = Project(
                title=form.title.data,
                description=form.description.data,
                category=form.category.data,
                category_color=form.category_color.data or 'primary',
                image_path=image_path,
                demo_url=form.demo_url.data,
                github_url=form.github_url.data,
                technologies=form.technologies.data,
                is_featured=form.is_featured.data
            )
            g.db.add(project)
            g.db.flush()  # Pour obtenir l'ID du projet

            # Gestion des documents
            if form.documents.data:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        # Sécuriser et sauvegarder le fichier
                        original_filename = file.filename
                        filename = secure_filename(original_filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # Créer l'entrée dans la base de données
                        document = ProjectDocument(
                            project_id=project.id,
                            filename=filename,
                            original_filename=original_filename,
                            file_path=os.path.join('uploads', filename).replace('\\', '/'),
                            file_size=os.path.getsize(file_path),
                            file_type=mimetypes.guess_type(original_filename)[0]
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
                file = form.image.data
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    project.image_path = os.path.join('uploads', filename).replace('\\', '/')

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
                        # Sécuriser et sauvegarder le fichier
                        original_filename = file.filename
                        filename = secure_filename(original_filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # Créer l'entrée dans la base de données
                        document = ProjectDocument(
                            project_id=project.id,
                            filename=filename,
                            original_filename=original_filename,
                            file_path=os.path.join('uploads', filename).replace('\\', '/'),
                            file_size=os.path.getsize(file_path),
                            file_type=mimetypes.guess_type(original_filename)[0]
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
    print(f"[DEBUG] Tentative de suppression du projet {project_id}")
    print(f"[DEBUG] Utilisateur connecté: {current_user.id}")
    print(f"[DEBUG] Méthode de la requête: {request.method}")
    print(f"[DEBUG] Headers de la requête: {dict(request.headers)}")
    print(f"[DEBUG] Données du formulaire: {dict(request.form)}")
    print(f"[DEBUG] Token CSRF dans la session: {session.get('csrf_token')}")
    print(f"[DEBUG] Token CSRF dans le formulaire: {request.form.get('csrf_token')}")
    
    # Vérifier le token CSRF
    if not request.form.get('csrf_token'):
        print("[DEBUG] Token CSRF manquant")
        flash('Token CSRF manquant.', 'danger')
        return redirect(url_for('project.projects'))
    
    project = g.db.query(Project).filter(Project.id == project_id).first()
    print(f"[DEBUG] Projet trouvé: {project is not None}")
    
    if not project:
        print("[DEBUG] Projet non trouvé")
        flash('Projet non trouvé.', 'danger')
        return redirect(url_for('project.projects'))
    
    try:
        print("[DEBUG] Début de la suppression")
        # Supprimer l'image si elle existe
        if project.image_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                   os.path.basename(project.image_path))
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[DEBUG] Image supprimée: {file_path}")
        
        # Supprimer les documents associés
        for document in project.documents:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[DEBUG] Document supprimé: {file_path}")
        
        # Supprimer le projet de la base de données
        g.db.delete(project)
        g.db.commit()
        print("[DEBUG] Suppression réussie")
        flash('Projet supprimé avec succès.', 'success')
    except Exception as e:
        print(f"[DEBUG] Erreur lors de la suppression: {str(e)}")
        g.db.rollback()
        print(f"Erreur lors de la suppression du projet : {e}")
        flash('Erreur lors de la suppression du projet.', 'danger')
    
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
    document = g.db.query(ProjectDocument).get_or_404(document_id)
    try:
        # Supprimer le fichier physique
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Supprimer l'entrée de la base de données
        g.db.delete(document)
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500