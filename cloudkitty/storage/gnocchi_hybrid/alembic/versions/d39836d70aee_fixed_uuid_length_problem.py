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
