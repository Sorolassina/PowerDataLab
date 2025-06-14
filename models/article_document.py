from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class ArticleDocument(Base):
    __tablename__ = 'article_documents'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id', ondelete='CASCADE'))
    filename = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    file_type = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    article = relationship("Article", back_populates="documents")

    def __repr__(self):
        return f"<ArticleDocument {self.original_filename}>" 