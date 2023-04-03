# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Creating indexes to allow SQL query optimizations
Revision ID: d875621d0384
Revises: c703a1bad612
Create Date: 2022-11-23 15:36:05.331585

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd875621d0384'
down_revision = 'c703a1bad612'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('idx_rated_data_frames_date', 'rated_data_frames',
                    ['begin', 'end'])
    op.create_index('idx_tenantid_begin_end', 'rated_data_frames',
                    ['tenant_id', 'begin', 'end'])


def downgrade():
    op.drop_index('idx_tenantid_begin_end', 'rated_data_frames')
    op.drop_index('idx_rated_data_frames_date', 'rated_data_frames')
