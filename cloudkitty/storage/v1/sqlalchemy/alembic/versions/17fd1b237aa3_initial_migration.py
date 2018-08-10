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

Revision ID: 17fd1b237aa3
Revises: None
Create Date: 2014-10-10 11:28:08.645122

"""

# revision identifiers, used by Alembic.
revision = '17fd1b237aa3'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'rated_data_frames',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('begin', sa.DateTime(), nullable=False),
        sa.Column('end', sa.DateTime(), nullable=False),
        sa.Column('unit', sa.String(length=255), nullable=False),
        sa.Column('qty', sa.Numeric(), nullable=False),
        sa.Column('res_type', sa.String(length=255), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('desc', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
