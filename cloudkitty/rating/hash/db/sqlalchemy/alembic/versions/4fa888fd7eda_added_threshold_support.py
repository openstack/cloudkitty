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

"""Added threshold support.

Revision ID: 4fa888fd7eda
Revises: 3dd7e13527f3
Create Date: 2015-05-05 14:39:24.562388

"""

# revision identifiers, used by Alembic.
revision = '4fa888fd7eda'
down_revision = '3dd7e13527f3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # NOTE(sheeprine): Hack to let the migrations pass for postgresql
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        constraints = ['uniq_field_threshold', 'uniq_service_threshold']
    else:
        constraints = ['uniq_field_mapping', 'uniq_service_mapping']
    op.create_table(
        'hashmap_thresholds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('threshold_id', sa.String(length=36), nullable=False),
        sa.Column('level', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('cost', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column(
            'map_type',
            sa.Enum('flat', 'rate', name='enum_map_type'),
            nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('field_id', sa.Integer(), nullable=True),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['field_id'],
            ['hashmap_fields.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['group_id'],
            ['hashmap_groups.id'],
            ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['service_id'],
            ['hashmap_services.id'],
            ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('threshold_id'),
        sa.UniqueConstraint('level', 'field_id', name=constraints[0]),
        sa.UniqueConstraint('level', 'service_id', name=constraints[1]),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
