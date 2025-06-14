from models.base import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class ProjectDocument(Base):
    __tablename__ = 'project_documents'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    filename = Column(Text, nullable=False)  # Nom du fichier stocké
    original_filename = Column(Text, nullable=False)  # Nom original du fichier
    file_path = Column(Text, nullable=False)  # Chemin relatif du fichier
    file_size = Column(Integer)  # Taille en bytes
    file_type = Column(Text)  # Type MIME du fichier
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relation avec le projet
    project = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<ProjectDocument {self.original_filename}>" 