#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

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
    op.create_table(
        'pyscripts_scripts',
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
