#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""Add start end dates and audit in hashmap mappings

Revision ID: 8a591f85865f
Revises: 4e0232ce
Create Date: 2023-03-06 14:22:00.000000

"""

from alembic import op
from cloudkitty import db
from cloudkitty.rating.common.db.migrations import create_common_tables
from cloudkitty.rating.hash.db.sqlalchemy import models

import datetime
import uuid

import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8a591f85865f'
down_revision = '4e0232ce'


def _update_start_date():
    # Timestamp zero.
    initial_start_date = datetime.datetime(year=1970, month=1, day=1,
                                           tzinfo=datetime.timezone.utc)
    with db.session_for_write() as session:
        q = session.query(models.HashMapMapping)
        mapping_db = q.with_for_update().all()
        for entry in mapping_db:
            entry.start = initial_start_date
            entry.name = uuid.uuid4().hex.replace('-', '')
            entry.created_by = 'migration'


def upgrade():
    table_name = 'hashmap_mappings'
    with op.batch_alter_table(
            table_name) as batch_op:
        # As we are not delete rows anymore, the constraint
        # validations will be delegated to the application.
        batch_op.drop_constraint(
            'uniq_field_mapping',
            type_='unique')
        batch_op.drop_constraint(
            'uniq_service_mapping',
            type_='unique')
        batch_op.add_column(
            sa.Column(
                'name',
                sa.String(length=32),
                nullable=False))
        create_common_tables(batch_op)

    _update_start_date()
