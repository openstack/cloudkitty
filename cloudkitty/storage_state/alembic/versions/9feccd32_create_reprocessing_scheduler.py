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

"""Create reprocessing scheduler table

Revision ID: 9feccd32
Revises: 4d69395f
Create Date: 2021-06-04 16:27:00.595274

"""
from alembic import op
import sqlalchemy

# revision identifiers, used by Alembic.
revision = '9feccd32'
down_revision = '4d69395f'


def upgrade():
    op.create_table(
        'storage_scope_reprocessing_schedule',
        sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column('identifier', sqlalchemy.String(length=256),
                          nullable=False, unique=False),
        sqlalchemy.Column('start_reprocess_time', sqlalchemy.DateTime,
                          nullable=False),
        sqlalchemy.Column('end_reprocess_time', sqlalchemy.DateTime,
                          nullable=False),
        sqlalchemy.Column('current_reprocess_time', sqlalchemy.DateTime,
                          nullable=True),
        sqlalchemy.Column('reason', sqlalchemy.Text, nullable=False),

        sqlalchemy.PrimaryKeyConstraint('id'),
        mysql_charset='utf8', mysql_engine='InnoDB'
    )
