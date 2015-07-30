"""Initial migration.

Revision ID: 4f9efa4601c0
Revises: None
Create Date: 2015-07-30 12:46:32.998770

"""

# revision identifiers, used by Alembic.
revision = '4f9efa4601c0'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('pyscripts_scripts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('script_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('checksum', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('script_id'),
    mysql_charset='utf8',
    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('pyscripts_scripts')
