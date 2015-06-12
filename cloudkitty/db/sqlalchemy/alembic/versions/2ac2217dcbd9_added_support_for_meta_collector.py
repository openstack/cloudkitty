"""Added support for meta collector

Revision ID: 2ac2217dcbd9
Revises: 464e951dc3b8
Create Date: 2014-09-25 12:41:28.585333

"""

# revision identifiers, used by Alembic.
revision = '2ac2217dcbd9'
down_revision = '464e951dc3b8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('service_to_collector_mappings',
    sa.Column('service', sa.String(length=255), nullable=False),
    sa.Column('collector', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('service'))


def downgrade():
    op.drop_table('service_to_collector_mappings')
