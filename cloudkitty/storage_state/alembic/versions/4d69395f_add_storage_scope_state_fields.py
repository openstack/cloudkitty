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

"""Update storage state constraint

Revision ID: 4d69395f
Revises: 750d3050cf71
Create Date: 2019-05-15 17:02:56.595274

"""
import importlib
import sqlalchemy

from alembic import op

# revision identifiers, used by Alembic.
revision = '4d69395f'
down_revision = '750d3050cf71'


def upgrade():
    down_version_module = importlib.import_module(
        "cloudkitty.storage_state.alembic.versions."
        "750d3050_create_last_processed_timestamp_column")

    for name, table in down_version_module.Base.metadata.tables.items():
        if name == 'cloudkitty_storage_states':
            with op.batch_alter_table(name,
                                      copy_from=table,
                                      recreate='always') as batch_op:
                batch_op.add_column(
                    sqlalchemy.Column('scope_activation_toggle_date',
                                      sqlalchemy.DateTime, nullable=False,
                                      server_default=sqlalchemy.sql.func.now())
                )
                batch_op.add_column(
                    sqlalchemy.Column('active', sqlalchemy.Boolean,
                                      nullable=False, default=True))
            break
