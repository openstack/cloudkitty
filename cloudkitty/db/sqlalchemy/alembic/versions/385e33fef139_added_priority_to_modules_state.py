"""Added priority to modules_state.

Revision ID: 385e33fef139
Revises: 2ac2217dcbd9
Create Date: 2015-03-17 17:50:15.229896

"""

# revision identifiers, used by Alembic.
revision = '385e33fef139'
down_revision = '2ac2217dcbd9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('modules_state',
                  sa.Column('priority', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('modules_state', 'priority')
