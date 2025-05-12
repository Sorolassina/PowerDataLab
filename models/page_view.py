from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class PageView(Base):
    __tablename__ = 'page_views'

    id = Column(Integer, primary_key=True)
    page = Column(Text, nullable=False)
    page_id = Column(Integer, ForeignKey('articles.id', ondelete='CASCADE'), nullable=True)
    ip_address = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=False)
    referrer = Column(Text)
    is_bot = Column(Integer, nullable=False, default=0)
    viewed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    article = relationship("Article", back_populates="page_views")

    def __repr__(self):
        return f"<PageView {self.id} on {self.page}>" 