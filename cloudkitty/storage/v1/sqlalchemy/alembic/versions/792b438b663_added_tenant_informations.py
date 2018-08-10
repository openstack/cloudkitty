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


def upgrade():
    op.add_column('rated_data_frames',
                  sa.Column('tenant_id', sa.String(length=32), nullable=True))
