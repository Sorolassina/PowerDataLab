from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class NewsletterSubscriber(Base):
    __tablename__ = 'newsletter_subscribers'

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    confirmed = Column(Text, nullable=False, default='false')
    status = Column(Text, nullable=False, default='active')
    subscribed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_newsletter = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<NewsletterSubscriber {self.email}>"

class Newsletter(Base):
    __tablename__ = 'newsletter'

    id = Column(Integer, primary_key=True)
    subject = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    article_ids = Column(Text)  # Stocké comme une chaîne de caractères
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Newsletter {self.subject}>"

class NewsletterHistory(Base):
    __tablename__ = 'newsletter_history'

    id = Column(Integer, primary_key=True)
    subject = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_by = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    recipient_count = Column(Integer, default=0)
    test_send = Column(Boolean, default=False)

    # Relations
    sender = relationship("User", back_populates="newsletter_history")
    
    @property
    def sent_at_formatted(self):
        """Retourne la date d'envoi formatée"""
        if self.sent_at:
            return self.sent_at.strftime("%d/%m/%Y à %H:%M")
        return "Non envoyé"
    
    @property
    def sender_name(self):
        """Retourne le nom de l'expéditeur"""
        if self.sender:
            return self.sender.username
        return "Système"
    
    def __repr__(self):
        return f"<NewsletterHistory {self.subject}>" 