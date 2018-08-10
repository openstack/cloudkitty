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

"""improve qty precision

Revision ID: 307430ab38bc
Revises: 792b438b663
Create Date: 2016-09-05 18:37:26.714065

"""

# revision identifiers, used by Alembic.
revision = '307430ab38bc'
down_revision = '792b438b663'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('rated_data_frames') as batch_op:
        batch_op.alter_column(
            'qty',
            type_=sa.Numeric(10, 5),
            existing_type=sa.Numeric())
