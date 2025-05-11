# PowerDataLab Blog

Blog professionnel développé avec Flask, présentant des articles sur Power BI, Power Apps, Power Automate, Power Virtual Agents et SharePoint.

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