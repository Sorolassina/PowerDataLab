"""update project status

Revision ID: update_project_status_01
Create Date: 2024-03-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'update_project_status_01'
down_revision = '28cebdb2509f'  # Pointe vers la dernière migration (convert_is_admin_to_boolean)
branch_labels = None
depends_on = None

def upgrade():
    # Ajouter d'abord la colonne status
    op.add_column('projects', sa.Column('status', sa.String(50), nullable=True))
    
    # Définir la valeur par défaut pour les projets existants
    op.execute("UPDATE projects SET status = 'En cours'")
    
    # Rendre la colonne non nullable après avoir défini les valeurs par défaut
    op.alter_column('projects', 'status',
        existing_type=sa.String(50),
        nullable=False,
        server_default='En cours'
    )

def downgrade():
    # Supprimer la colonne status
    op.drop_column('projects', 'status') 