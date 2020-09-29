# Copyright 2018 OpenStack Foundation
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

"""Increase cost fields to 30 digits

Revision ID: Ifbf5b2515c7
Revises: 644faa4491fd
Create Date: 2020-09-29 14:22:00.000000

"""

from alembic import op
import importlib

import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'Ifbf5b2515c7'
down_revision = '644faa4491fd'


def upgrade():
    down_version_module = importlib.import_module(
        "cloudkitty.rating.hash.db.sqlalchemy.alembic.versions."
        "644faa4491fd_update_tenant_id_type_from_uuid_to_text")

    for table_name in ('hashmap_mappings', 'hashmap_thresholds'):
        with op.batch_alter_table(
                table_name, reflect_args=down_version_module.get_reflect(
                    table_name)) as batch_op:

            batch_op.alter_column('cost',
                                  type_=sa.Numeric(precision=30, scale=28))
