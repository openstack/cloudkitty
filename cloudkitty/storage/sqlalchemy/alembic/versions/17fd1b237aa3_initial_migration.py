"""Initial migration

Revision ID: 17fd1b237aa3
Revises: None
Create Date: 2014-10-10 11:28:08.645122

"""

# revision identifiers, used by Alembic.
revision = '17fd1b237aa3'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('rated_data_frames',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('begin', sa.DateTime(), nullable=False),
    sa.Column('end', sa.DateTime(), nullable=False),
    sa.Column('unit', sa.String(length=255), nullable=False),
    sa.Column('qty', sa.Numeric(), nullable=False),
    sa.Column('res_type', sa.String(length=255), nullable=False),
    sa.Column('rate', sa.Float(), nullable=False),
    sa.Column('desc', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8',
    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('rated_data_frames')
    op.drop_table('storage_sqlalchemy_alembic')
