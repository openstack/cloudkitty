"""added tenant informations

Revision ID: 792b438b663
Revises: 17fd1b237aa3
Create Date: 2014-12-02 13:12:11.328534

"""

# revision identifiers, used by Alembic.
revision = '792b438b663'
down_revision = '17fd1b237aa3'

from alembic import op
import sqlalchemy as sa

from cloudkitty.storage.sqlalchemy import models


def upgrade():
    op.add_column('rated_data_frames',
                  sa.Column('tenant_id', sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column('rated_data_frames', 'tenant_id')
