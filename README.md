# PowerDataLab

Une plateforme web moderne pour partager des ressources et des projets autour de la suite Microsoft Power Platform.

## Fonctionnalités

- Articles et tutoriels sur Power BI, Power Apps, Power Automate et SharePoint
- Projets téléchargeables avec code source et documentation
- Système de likes et de vues
- Authentification des utilisateurs
- Emails de bienvenue personnalisés
- Interface moderne et responsive

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-username/powerdatalab.git
cd powerdatalab
```

2. Créez un environnement virtuel et installez les dépendances :
```bash
python -m venv venv
source venv/bin/activate  # ou `venv\Scripts\activate` sous Windows
pip install -r requirements.txt
```

3. Créez un fichier `.env` avec les variables d'environnement suivantes :
```
# Configuration générale
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=votre-clé-secrète-très-longue-et-aléatoire
SITE_URL=http://localhost:5000

# Configuration de la base de données
DATABASE_URL=sqlite:///app.db

# Configuration email (exemple avec Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=votre-email@gmail.com
MAIL_PASSWORD=votre-mot-de-passe-d-application
MAIL_DEFAULT_SENDER=PowerDataLab <votre-email@gmail.com>

# Configuration du logging
LOG_TO_STDOUT=false
LOG_LEVEL=INFO
```

Note : Pour Gmail, vous devez :
1. Activer l'authentification à deux facteurs
2. Générer un mot de passe d'application spécifique
3. Utiliser ce mot de passe d'application comme MAIL_PASSWORD

4. Initialisez la base de données :
```bash
flask db upgrade
```

5. Lancez l'application :
```bash
flask run
```

L'application sera accessible à l'adresse http://localhost:5000

## Structure du projet

```
powerdatalab/
├── app/                    # Application Flask
│   ├── static/            # Fichiers statiques (CSS, JS, images)
│   ├── templates/         # Templates Jinja2
│   │   └── email/        # Templates d'emails
│   ├── models/           # Modèles SQLAlchemy
│   └── utils/            # Utilitaires (email, auth, etc.)
├── migrations/            # Migrations Alembic
├── tests/                # Tests unitaires et d'intégration
├── config.py             # Configuration de l'application
├── requirements.txt      # Dépendances Python
└── README.md            # Ce fichier
```

## Développement

Pour contribuer au projet :

1. Créez une branche pour votre fonctionnalité :
```bash
git checkout -b feature/ma-fonctionnalite
```

2. Faites vos modifications et commitez :
```bash
git add .
git commit -m "Description de vos modifications"
```

3. Poussez vos modifications :
```bash
git push origin feature/ma-fonctionnalite
```

4. Créez une Pull Request sur GitHub

## Tests

Pour lancer les tests :
```bash
pytest
```

## Déploiement

Instructions pour le déploiement en production à venir...

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## 🚀 Déploiement sur Render

### Prérequis
- Un compte [Render](https://render.com)
- Un compte [GitHub](https://github.com)
- Un compte Gmail pour les notifications

### Étapes de déploiement

1. **Préparation du dépôt**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <votre-repo-github>
   git push -u origin main
   ```

2. **Configuration sur Render**
   - Connectez-vous sur [Render](https://render.com)
   - Cliquez sur "New +" et sélectionnez "Web Service"
   - Connectez votre dépôt GitHub
   - Sélectionnez le dépôt du blog

3. **Configuration des variables d'environnement**
   Dans l'interface Render, configurez les variables suivantes :
   ```
   MAIL_USERNAME=votre-email@gmail.com
   MAIL_PASSWORD=votre-mot-de-passe-application
   MAIL_DEFAULT_SENDER=votre-email@gmail.com
   ```

4. **Déploiement**
   - Render détectera automatiquement le `render.yaml`
   - Cliquez sur "Create Web Service"
   - Attendez que le déploiement soit terminé

## 🐳 Déploiement local avec Docker

### Prérequis
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Étapes de déploiement local

1. **Création du fichier .env**
   ```bash
   cp .env.example .env
   ```
   Remplissez les variables dans le fichier `.env`

2. **Construction de l'image**
   ```bash
   docker build -t powerdatalab-blog .
   ```

3. **Lancement du conteneur**
   ```bash
   docker run -p 5000:5000 --env-file .env powerdatalab-blog
   ```

4. **Accès à l'application**
   Ouvrez votre navigateur et accédez à `http://localhost:5000`

## 🔧 Développement local

### Prérequis
- Python 3.9+
- pip
- virtualenv

### Installation

1. **Cloner le dépôt**
   ```bash
   git clone <votre-repo-github>
   cd Monblog
   ```

2. **Créer et activer l'environnement virtuel**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement**
   ```bash
   cp .env.example .env
   ```
   Remplissez les variables dans le fichier `.env`

5. **Initialiser la base de données**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Lancer l'application**
   ```bash
   python app.py
   ```

## 📝 Structure du projet

```
Monblog/
├── app.py              # Application principale
├── models.py           # Modèles de données
├── requirements.txt    # Dépendances Python
├── Dockerfile         # Configuration Docker
├── render.yaml        # Configuration Render
├── .env              # Variables d'environnement
├── static/           # Fichiers statiques
│   ├── css/         # Styles CSS
│   ├── js/          # Scripts JavaScript
│   └── uploads/     # Images uploadées
└── templates/        # Templates HTML
    ├── admin/       # Templates d'administration
    └── ...          # Autres templates
```

## 🔐 Sécurité

- Les mots de passe sont hashés avec Werkzeug
- Protection CSRF sur tous les formulaires
- Validation des entrées utilisateur
- Protection contre les injections SQL
- Gestion sécurisée des sessions

## 📧 Configuration Email

Pour configurer les notifications email :

1. Activez l'authentification à deux facteurs sur votre compte Gmail
2. Générez un mot de passe d'application :
   - Allez dans les paramètres de votre compte Google
   - Sécurité > Authentification à 2 facteurs
   - Mots de passe d'application
   - Générez un nouveau mot de passe pour l'application

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence propriétaire. Tous droits réservés.

**Restrictions :**
- Utilisation commerciale interdite
- Distribution ou modification non autorisée
- Usage strictement personnel et éducatif uniquement
- Toute reproduction nécessite une autorisation écrite de l'auteur

Copyright © 2024 Lassina SORO. Tous droits réservés.

## 👤 Contact

Lassina SORO - [LinkedIn](https://linkedin.com/in/sorolassina)

Email: sorolassina58@gmail.com 