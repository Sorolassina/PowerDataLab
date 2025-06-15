from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, URL, Optional
from wtforms import TextAreaField, SelectField, FileField
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, BooleanField
from models.project import Project  # Importer le modèle Project

class NewsletterForm(FlaskForm):
    subject = StringField('Sujet', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Mot de passe', validators=[DataRequired()])

class ArticleForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    category = SelectField('Catégorie', coerce=int, validators=[DataRequired()])
    images = FileField('Images', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    tags = StringField('Tags')
    
# Définition des formulaires
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')

class RegisterForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])

class AdminVerifyForm(FlaskForm):
    code = StringField('Code de vérification', validators=[DataRequired(), Length(min=6, max=6)])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])   

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, BooleanField
from wtforms.validators import DataRequired, URL

class ProjectForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Catégorie', validators=[DataRequired()], choices=[
        ('power-bi', 'Power BI'),
        ('power-apps', 'Power Apps'),
        ('power-automate', 'Power Automate'),
        ('sharepoint', 'SharePoint'),
        ('python', 'Python'),
        ('data-analysis', 'Analyse de données')
    ])
    category_color = StringField('Couleur de la catégorie')
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    demo_url = StringField('Lien Démo', validators=[Optional(), URL(message="L'URL n'est pas valide")])
    github_url = StringField('Lien GitHub', validators=[Optional(), URL(message="L'URL n'est pas valide")])
    documents = FileField('Documents', validators=[Optional(),
        FileAllowed(['pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx'], 
        'Documents uniquement (PDF, Word, TXT, Markdown, PowerPoint, Excel)!')
    ], render_kw={"multiple": True})
    technologies = StringField('Technologies (séparées par des virgules)')
    is_featured = BooleanField('Projet phare')
    status = SelectField('Statut', validators=[DataRequired()], choices=[
        (Project.STATUS_DRAFT, 'En cours'),
        (Project.STATUS_PUBLISHED, 'Terminé'),
        (Project.STATUS_ARCHIVED, 'Archivé'),
        (Project.STATUS_CANCELED, 'Annulé'),
        (Project.STATUS_ON_HOLD, 'En pause'),
    ])
    