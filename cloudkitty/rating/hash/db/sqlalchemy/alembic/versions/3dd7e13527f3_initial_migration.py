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

"""Initial migration

Revision ID: 3dd7e13527f3
Revises: None
Create Date: 2015-03-10 13:06:41.067563

"""

# revision identifiers, used by Alembic.
revision = '3dd7e13527f3'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'hashmap_services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('service_id'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
    op.create_table(
        'hashmap_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['service_id'],
            ['hashmap_services.id'],
            ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('field_id'),
        sa.UniqueConstraint('field_id', 'name', name='uniq_field'),
        sa.UniqueConstraint(
            'service_id',
            'name',
            name='uniq_map_service_field'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
    op.create_table(
        'hashmap_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id'),
        sa.UniqueConstraint('name'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
    op.create_table(
        'hashmap_maps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mapping_id', sa.String(length=36), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=True),
        sa.Column('cost', sa.Numeric(20, 8), nullable=False),
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
        sa.UniqueConstraint('mapping_id'),
        sa.UniqueConstraint(
            'value',
            'field_id',
            name='uniq_field_mapping'),
        sa.UniqueConstraint(
            'value',
            'service_id',
            name='uniq_service_mapping'),
        mysql_charset='utf8',
        mysql_engine='InnoDB')
