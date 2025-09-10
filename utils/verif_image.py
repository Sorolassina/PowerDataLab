from models.base import SessionLocal
from models.article import Article
import os
from datetime import datetime
from flask import current_app, g

# Fonction pour vérifier les extensions de fichiers autorisées
def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """Vérifie si l'extension du fichier est une image autorisée"""
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_video_file(filename):
    """Vérifie si l'extension du fichier est une vidéo autorisée"""
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def get_file_type(filename):
    """Détermine le type de fichier (image ou vidéo)"""
    if allowed_image_file(filename):
        return 'image'
    elif allowed_video_file(filename):
        return 'video'
    else:
        return 'unknown'

def clean_duplicate_images():
    """Nettoie les images en double dans le dossier uploads."""
    print("Début du nettoyage des images...")
    upload_dir = current_app.config['UPLOAD_FOLDER']
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
        parts = filename.split('_')
        if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:  # Format timestamp
            base_name = '_'.join(parts[2:])
        else:
            base_name = filename
            
        file_path = os.path.join(upload_dir, filename)
        mod_time = os.path.getmtime(file_path)
        print(f"Traitement du fichier: {filename}")
        print(f"  - Nom de base: {base_name}")
        print(f"  - Date de modification: {datetime.fromtimestamp(mod_time)}")
        
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
    articles = g.db.query(Article).filter(Article.image_path.isnot(None)).all()
    
    for article in articles:
        if not article.image_path:
            continue
            
        # Séparer les chemins d'images
        image_paths = article.image_path.split(',')
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
            article.image_path = ','.join(valid_paths)
            print(f"Article {article.id} mis à jour avec {len(valid_paths)} images valides")
        else:
            article.image_path = None
            print(f"Article {article.id} mis à jour: aucune image valide") 
    try:
        g.db.commit()
        print("\nNettoyage terminé.")
    except Exception as e:
        g.db.rollback()
        print(f"\nErreur lors de la mise à jour de la base de données: {e}")