# Copyright 2019 Objectif Libre
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

Revision ID: c50ed2c19204
Revises: d9d103dd4dcf
Create Date: 2019-05-15 17:02:56.595274

"""
from alembic import op
import six

from cloudkitty.storage_state import models

# revision identifiers, used by Alembic.
revision = 'c50ed2c19204'
down_revision = 'd9d103dd4dcf'
branch_labels = None
depends_on = None


def upgrade():
    for name, table in six.iteritems(models.Base.metadata.tables):
        if name == 'cloudkitty_storage_states':

            with op.batch_alter_table(name,
                                      copy_from=table,
                                      recreate='always') as batch_op:
                batch_op.alter_column('identifier')
                batch_op.create_unique_constraint(
                    'uq_cloudkitty_storage_states_identifier',
                    ['identifier', 'scope_key', 'collector', 'fetcher'])

            break
