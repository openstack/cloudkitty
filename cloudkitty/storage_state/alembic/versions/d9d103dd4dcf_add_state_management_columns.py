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

"""Add details to state management

Revision ID: d9d103dd4dcf
Revises: c14eea9d3cc1
Create Date: 2019-02-07 13:59:39.294277

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9d103dd4dcf'
down_revision = 'c14eea9d3cc1'
branch_labels = None
depends_on = None


def upgrade():
    for column_name in ('scope_key', 'collector', 'fetcher'):
        op.add_column(
            'cloudkitty_storage_states',
            sa.Column(column_name, sa.String(length=40), nullable=True))
