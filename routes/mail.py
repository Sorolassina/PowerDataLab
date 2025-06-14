from flask_mail import Mail
from flask import current_app
from flask_mail import Message

mail = Mail()

def init_mail(app):
    """Initialise Flask-Mail avec l'application Flask"""
    # Configuration de Flask-Mail
    app.config['MAIL_SERVER'] = app.config.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(app.config.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = bool(app.config.get('MAIL_USE_TLS', True))
    app.config['MAIL_USERNAME'] = app.config.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = app.config.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = app.config.get('MAIL_DEFAULT_SENDER')
    
    # Initialisation de Flask-Mail
    mail.init_app(app)

def send_reset_password_email(user_email, reset_token):
    """Envoie un email de réinitialisation de mot de passe"""
    reset_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/reset-password/{reset_token}"
    msg = Message(
        'Réinitialisation de votre mot de passe',
        recipients=[user_email]
    )
    msg.body = f"""Pour réinitialiser votre mot de passe, visitez le lien suivant :
{reset_url}

Si vous n'avez pas demandé de réinitialisation de mot de passe, ignorez cet email.
"""
    mail.send(msg)

def send_verification_email(user_email, verification_token):
    """Envoie un email de vérification d'adresse email"""
    verification_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/verify-email/{verification_token}"
    msg = Message(
        'Vérification de votre adresse email',
        recipients=[user_email]
    )
    msg.body = f"""Pour vérifier votre adresse email, visitez le lien suivant :
{verification_url}

Si vous n'avez pas créé de compte, ignorez cet email.
"""
    mail.send(msg) 