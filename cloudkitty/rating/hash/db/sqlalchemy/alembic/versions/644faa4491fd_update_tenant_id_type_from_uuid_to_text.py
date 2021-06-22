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

"""Update tenant_id type from uuid to text

Revision ID: 644faa4491fd
Revises: 4da82e1c11c8
Create Date: 2018-10-29 17:25:37.901136

"""

# revision identifiers, used by Alembic.
revision = '644faa4491fd'
down_revision = '4da82e1c11c8'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


CONSTRAINT_MAP = {
    'hashmap_mappings': {
        'uniq_field_mapping': (
            ['value', 'field_id', 'tenant_id'],
            ['value', 'field_id']),
        'uniq_service_mapping': (
            ['value', 'service_id', 'tenant_id'],
            ['value', 'service_id'])},
    'hashmap_thresholds': {
        'uniq_field_threshold': (
            ['level', 'field_id', 'tenant_id'],
            ['level', 'field_id']),
        'uniq_service_threshold': (
            ['level', 'service_id', 'tenant_id'],
            ['level', 'service_id'])}}


def get_reflect(table):
    reflect_args = [
        sa.Column(
            'service_id',
            sa.Integer,
            sa.ForeignKey(
                'hashmap_services.id',
                ondelete='CASCADE',
                name='fk_{}_service_id_hashmap_services'.format(table)),
            nullable=True),
        sa.Column(
            'field_id',
            sa.Integer,
            sa.ForeignKey(
                'hashmap_fields.id',
                ondelete='CASCADE',
                name='fk_{}_field_id_hashmap_fields'.format(table)),
            nullable=True),
        sa.Column(
            'group_id',
            sa.Integer,
            sa.ForeignKey(
                'hashmap_groups.id',
                ondelete='SET NULL',
                name='fk_{}_group_id_hashmap_groups'.format(table)),
            nullable=True),
        sa.Column(
            'map_type',
            sa.Enum(
                'flat',
                'rate',
                name='enum_{}map_type'.format(
                    'hash' if table == 'hashmap_thresholds' else ''),
                create_constraint=True),
            nullable=False)]
    return reflect_args


def upgrade():
    for table in ('hashmap_mappings', 'hashmap_thresholds'):
        with op.batch_alter_table(
            table,
            reflect_args=get_reflect(table)
        ) as batch_op:
            batch_op.alter_column('tenant_id',
                                  type_=sa.String(length=255),
                                  existing_nullable=True)
            for name, columns in CONSTRAINT_MAP[table].items():
                batch_op.drop_constraint(name, type_='unique')
                batch_op.create_unique_constraint(name, columns[0])
