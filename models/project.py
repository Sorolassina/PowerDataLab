from models.base import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

class Project(Base):
    __tablename__ = 'projects'

    # Constantes pour les statuts
    STATUS_DRAFT = 'En cours'
    STATUS_PUBLISHED = 'Terminé'
    STATUS_ARCHIVED = 'Archivé'
    STATUS_CANCELED = 'Annulé'
    STATUS_ON_HOLD = 'En pause'

    # Mapping des statuts avec leurs icônes
    STATUS_ICONS = {
        STATUS_DRAFT: 'fas fa-tools',           # Outils en cours
        STATUS_PUBLISHED: 'fas fa-check-circle', # Coche dans un cercle
        STATUS_ARCHIVED: 'fas fa-archive',       # Boîte d'archive
        STATUS_CANCELED: 'fas fa-times-circle',  # X dans un cercle
        STATUS_ON_HOLD: 'fas fa-pause-circle'    # Pause dans un cercle
    }

    # Mapping des statuts avec leurs couleurs
    STATUS_COLORS = {
        STATUS_DRAFT: 'info',        # Bleu info
        STATUS_PUBLISHED: 'success', # Vert
        STATUS_ARCHIVED: 'secondary', # Gris
        STATUS_CANCELED: 'danger',   # Rouge
        STATUS_ON_HOLD: 'warning'    # Orange
    }

    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    category_color = Column(String(20), default='primary')
    image_path = Column(String(255))
    demo_url = Column(String(255))
    github_url = Column(String(255))
    documentation_url = Column(String(255))
    technologies = Column(String(255))  # Stocker sous forme de chaîne séparée par des virgules
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    status = Column(String(50), default=STATUS_DRAFT)
    

    # Relation avec les documents
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")

    @property
    def status_icon(self):
        """Retourne l'icône Font Awesome correspondant au statut"""
        return self.STATUS_ICONS.get(self.status, 'fas fa-question-circle')

    @property
    def status_color(self):
        """Retourne la classe de couleur Bootstrap correspondant au statut"""
        return self.STATUS_COLORS.get(self.status, 'primary')