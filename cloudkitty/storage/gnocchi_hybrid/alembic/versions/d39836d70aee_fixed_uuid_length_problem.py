"""Fixed UUID length problem.

Revision ID: d39836d70aee
Revises: 4c2f20df7491
Create Date: 2016-05-11 14:04:10.984006

"""

# revision identifiers, used by Alembic.
revision = 'd39836d70aee'
down_revision = '4c2f20df7491'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('ghybrid_dataframes') as batch_op:
        batch_op.alter_column(
            'resource_ref',
            type_=sa.String(36),
            existing_type=sa.String(32))


def downgrade():
    with op.batch_alter_table('ghybrid_dataframes') as batch_op:
        batch_op.alter_column(
            'resource_ref',
            type_=sa.String(32),
            existing_type=sa.String(36))
