from .category import category_bp
from .article import article_bp
from .main import main_bp
from .admin import admin_bp
from .comment import comment_bp
from .users import user_bp
from .project import project_bp

# Liste de tous les blueprints à enregistrer
blueprints = [
    category_bp,
    article_bp,
    comment_bp,
    main_bp,
    admin_bp,
    user_bp,
    project_bp
] 