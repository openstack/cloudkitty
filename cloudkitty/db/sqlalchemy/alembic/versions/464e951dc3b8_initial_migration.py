"""Initial migration

Revision ID: 464e951dc3b8
Revises: None
Create Date: 2014-08-05 17:41:34.470183

"""

# revision identifiers, used by Alembic.
revision = '464e951dc3b8'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('states',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('state', sa.BigInteger(), nullable=False),
    sa.Column('s_metadata', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('name'))
    op.create_table('modules_state',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('state', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('name'))


def downgrade():
    op.drop_table('modules_state')
    op.drop_table('states')
