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

"""Add start end dates and audit in pyscripts

Revision ID: c6e4cda29654
Revises: 75c205f6f1a2
Create Date: 2023-03-06 14:22:00.000000

"""

from alembic import op
from cloudkitty import db
from cloudkitty.rating.common.db.migrations import create_common_tables
from cloudkitty.rating.pyscripts.db.sqlalchemy import models

import datetime


# revision identifiers, used by Alembic.
revision = 'c6e4cda29654'
down_revision = '75c205f6f1a2'


def _update_start_date():
    # Year of the start of the project (not the first version)
    initial_start_date = datetime.datetime(year=2014, month=1, day=1)
    with db.session_for_write() as session:
        q = session.query(models.PyScriptsScript)
        mapping_db = q.with_for_update().all()
        for entry in mapping_db:
            entry.start = initial_start_date
            entry.created_by = 'migration'


def upgrade():
    table_name = 'pyscripts_scripts'
    is_sqlite = op.get_context().dialect.name == 'sqlite'
    with op.batch_alter_table(
            table_name) as batch_op:
        if not is_sqlite:
            batch_op.drop_constraint(
                'name',
                type_='unique')
        create_common_tables(batch_op)

    _update_start_date()
