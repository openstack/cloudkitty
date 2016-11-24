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
    op.create_table(
        'service_to_collector_mappings',
        sa.Column('service', sa.String(length=255), nullable=False),
        sa.Column('collector', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('service'))
