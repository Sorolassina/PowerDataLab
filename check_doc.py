from models.base import SessionLocal
from models.project_document import ProjectDocument

def check_document(document_id):
    db = SessionLocal()
    try:
        document = db.query(ProjectDocument).filter(ProjectDocument.id == document_id).first()
        if document:
            print(f"Document trouvé :")
            print(f"ID : {document.id}")
            print(f"Nom original : {document.original_filename}")
            print(f"Nom du fichier : {document.filename}")
            print(f"Chemin du fichier : {document.file_path}")
            print(f"Type de fichier : {document.file_type}")
            print(f"Taille : {document.file_size} bytes")
            print(f"Project ID : {document.project_id}")
        else:
            print(f"Aucun document trouvé avec l'ID {document_id}")
    finally:
        db.close()

if __name__ == "__main__":
    check_document(12)  # Vérifie le document avec l'ID 12 