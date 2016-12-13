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

"""Add per tenant hashmap support

Revision ID: 4da82e1c11c8
Revises: c88a06b1cfce
Create Date: 2016-05-31 12:27:30.821497

"""

# revision identifiers, used by Alembic.
revision = '4da82e1c11c8'
down_revision = 'c88a06b1cfce'

from alembic import op
import sqlalchemy as sa

CONSTRAINT_MAP = {
    'hashmap_mappings': {
        u'uniq_field_mapping': (
            ['value', 'field_id', 'tenant_id'],
            ['value', 'field_id']),
        u'uniq_service_mapping': (
            ['value', 'service_id', 'tenant_id'],
            ['value', 'service_id'])},
    'hashmap_thresholds': {
        u'uniq_field_threshold': (
            ['level', 'field_id', 'tenant_id'],
            ['level', 'field_id']),
        u'uniq_service_threshold': (
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
                    'hash' if table == 'hashmap_thresholds' else '')),
            nullable=False)]
    return reflect_args


def upgrade():
    for table in ('hashmap_mappings', 'hashmap_thresholds'):
        with op.batch_alter_table(
            table,
            reflect_args=get_reflect(table)
        ) as batch_op:
            batch_op.add_column(
                sa.Column(
                    'tenant_id',
                    sa.String(length=36),
                    nullable=True))
            for name, columns in CONSTRAINT_MAP[table].items():
                batch_op.drop_constraint(name, type_='unique')
                batch_op.create_unique_constraint(name, columns[0])
