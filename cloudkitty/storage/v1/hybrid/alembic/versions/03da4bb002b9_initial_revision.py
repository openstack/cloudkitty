# -*- coding: utf-8 -*-
# Copyright 2017 Objectif Libre
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
# @author: Luka Peschke
#
"""initial revision

Revision ID: 03da4bb002b9
Revises: None
Create Date: 2017-11-21 15:59:26.776639

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03da4bb002b9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'hybrid_storage_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=32), nullable=False),
        sa.Column('state', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
