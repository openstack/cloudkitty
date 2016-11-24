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

"""Added priority to modules_state.

Revision ID: 385e33fef139
Revises: 2ac2217dcbd9
Create Date: 2015-03-17 17:50:15.229896

"""

# revision identifiers, used by Alembic.
revision = '385e33fef139'
down_revision = '2ac2217dcbd9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'modules_state',
        sa.Column('priority', sa.Integer(), nullable=True))
