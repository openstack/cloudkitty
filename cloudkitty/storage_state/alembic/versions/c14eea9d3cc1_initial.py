# -*- coding: utf-8 -*-
# Copyright 2018 Objectif Libre
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
"""Initial

Revision ID: c14eea9d3cc1
Revises:
Create Date: 2018-04-20 14:27:11.434366

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c14eea9d3cc1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cloudkitty_storage_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier',
                  sa.String(length=40),
                  nullable=False,
                  unique=True),
        sa.Column('state', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_engine='InnoDB'
    )


def downgrade():
    op.drop_table('cloudkitty_storage_states')
