"""Initial migration.

Revision ID: 4c2f20df7491
Revises: None
Create Date: 2015-11-18 11:44:09.175326

"""

# revision identifiers, used by Alembic.
revision = '4c2f20df7491'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ghybrid_dataframes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('begin', sa.DateTime(), nullable=False),
    sa.Column('end', sa.DateTime(), nullable=False),
    sa.Column('res_type', sa.String(length=255), nullable=False),
    sa.Column('rate', sa.Numeric(precision=20, scale=8), nullable=False),
    sa.Column('resource_ref', sa.String(length=32), nullable=False),
    sa.Column('tenant_id', sa.String(length=32), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8',
    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('ghybrid_dataframes')
