# Copyright 2019 OpenStack Foundation
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

"""move from sha1 to sha512

Revision ID: 75c205f6f1a2
Revises: 4f9efa4601c0
Create Date: 2019-03-25 13:53:23.398755

"""

# revision identifiers, used by Alembic.
revision = '75c205f6f1a2'
down_revision = '4f9efa4601c0'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    with op.batch_alter_table('pyscripts_scripts') as batch_op:
        batch_op.alter_column('checksum',
                              existing_type=sa.VARCHAR(length=40),
                              type_=sa.String(length=128))


def downgrade():
    with op.batch_alter_table('pyscripts_scripts') as batch_op:
        batch_op.alter_column('checksum',
                              existing_type=sa.String(length=128),
                              type_=sa.VARCHAR(length=40))
