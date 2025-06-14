import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template
from smtplib import SMTP, SMTPException

logger = logging.getLogger(__name__)

class EmailError(Exception):
    """Exception personnalisée pour les erreurs d'envoi d'email."""
    pass

def send_email(
    to_email: str,
    subject: str,
    template: str,
    template_params: Optional[Dict[str, Any]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None
) -> bool:
    """
    Envoie un email en utilisant un template HTML.
    
    Args:
        to_email: Adresse email du destinataire
        subject: Sujet de l'email
        template: Nom du template HTML (sans l'extension)
        template_params: Paramètres à passer au template
        cc: Liste des adresses en copie
        bcc: Liste des adresses en copie cachée
    
    Returns:
        bool: True si l'envoi a réussi, False sinon
    
    Raises:
        EmailError: Si une erreur survient pendant l'envoi
    """
    if template_params is None:
        template_params = {}
    
    # Ajout de paramètres communs
    template_params['now'] = datetime.now()
    
    try:
        # Création du message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_app.config['MAIL_USERNAME']
        msg['To'] = to_email
        
        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
        
        # Rendu du template
        html_content = render_template(f'email/{template}.html', **template_params)
        msg.attach(MIMEText(html_content, 'html'))
        
        # Configuration SMTP
        with SMTP(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT']
        ) as server:
            if current_app.config['MAIL_USE_TLS']:
                server.starttls()
            
            if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
                server.login(
                    current_app.config['MAIL_USERNAME'],
                    current_app.config['MAIL_PASSWORD']
                )
            
            # Liste complète des destinataires
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Envoi
            server.send_message(msg, to_addrs=recipients)
            
            logger.info(
                f"Email envoyé avec succès à {to_email} "
                f"(cc: {cc or 'aucun'}, bcc: {bcc or 'aucun'})"
            )
            return True
            
    except SMTPException as e:
        error_msg = f"Erreur SMTP lors de l'envoi à {to_email}: {str(e)}"
        logger.error(error_msg)
        raise EmailError(error_msg)
        
    except Exception as e:
        error_msg = f"Erreur inattendue lors de l'envoi à {to_email}: {str(e)}"
        logger.error(error_msg)
        raise EmailError(error_msg)

def send_welcome_email(user_email: str, username: str) -> bool:
    """
    Envoie l'email de bienvenue à un nouvel utilisateur.
    
    Args:
        user_email: Email de l'utilisateur
        username: Nom d'utilisateur
        
    Returns:
        bool: True si l'envoi a réussi
    """
    try:
        return send_email(
            to_email=user_email,
            subject="Bienvenue sur PowerDataAnalytics !",
            template="welcome",
            template_params={
                'username': username,
                'login_url': current_app.config['SITE_URL'] + '/login'
            }
        )
    except EmailError as e:
        logger.error(f"Échec de l'envoi de l'email de bienvenue à {user_email}: {str(e)}")
        return False

def send_admin_code(admin_email: str, admin_name: str, admin_code: str) -> bool:
    """
    Envoie le code d'accès administrateur par email.
    
    Args:
        admin_email: Email de l'administrateur
        admin_name: Nom de l'administrateur
        admin_code: Code d'accès généré
        
    Returns:
        bool: True si l'envoi a réussi
    """
    try:
        return send_email(
            to_email=admin_email,
            subject="Code d'accès administrateur PowerDataAnalytics",
            template="admin_code",
            template_params={
                'admin_name': admin_name,
                'admin_code': admin_code
            }
        )
    except EmailError as e:
        logger.error(f"Échec de l'envoi du code admin à {admin_email}: {str(e)}")
        return False 