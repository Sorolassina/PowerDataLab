from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    color_theme = Column(Text, default='#000000')
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    articles = relationship("Article", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category {self.name}>" 