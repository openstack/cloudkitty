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
    op.create_table(
        'states',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('state', sa.BigInteger(), nullable=False),
        sa.Column('s_metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('name'))
    op.create_table(
        'modules_state',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('state', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('name'))
