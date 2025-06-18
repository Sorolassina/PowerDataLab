from flask import Blueprint, send_from_directory, current_app, request
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.verif_image import allowed_file

uploads_bp = Blueprint('uploads', __name__)

def allowed_document(filename):
    """Vérifie si l'extension du document est autorisée"""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, file_type='image'):
    """Fonction générique pour sauvegarder un fichier
    file_type peut être 'image' ou 'document'
    Retourne le chemin relatif du fichier sauvegardé
    """
    if file and file.filename:
        if (file_type == 'image' and allowed_file(file.filename)) or \
           (file_type == 'document' and allowed_document(file.filename)):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # S'assurer que le dossier existe
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Sauvegarder le fichier
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Retourner le chemin relatif (pour la base de données)
            return os.path.join('uploads', unique_filename).replace('\\', '/')
    return None

def save_files(files, file_type='image'):
    """Sauvegarde plusieurs fichiers et retourne la liste des chemins"""
    paths = []
    for file in files:
        path = save_file(file, file_type)
        if path:
            paths.append(path)
    return paths

def delete_file(filename):
    """Supprime un fichier du système de fichiers"""
    if filename:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(filename))
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    return False

@uploads_bp.route('/data/uploads/<path:filename>')
def serve_upload(filename):
    """Sert les fichiers depuis le dossier UPLOAD_FOLDER"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename) 