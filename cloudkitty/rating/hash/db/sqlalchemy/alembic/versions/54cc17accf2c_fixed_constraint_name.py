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

"""Fixed constraint name.

Revision ID: 54cc17accf2c
Revises: 4fa888fd7eda
Create Date: 2015-05-28 16:44:32.936076

"""

# revision identifiers, used by Alembic.
revision = '54cc17accf2c'
down_revision = '4fa888fd7eda'

from alembic import op
import sqlalchemy as sa


def create_table(is_old=False):
    if is_old:
        constraints = ['uniq_field_mapping', 'uniq_service_mapping']
    else:
        constraints = ['uniq_field_threshold', 'uniq_service_threshold']
    table = op.create_table(
        'tmig_hashmap_thresholds',
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
        sa.UniqueConstraint('level', 'service_id', name=constraints[1]))
    return table


def upgrade():
    dialect = op.get_context().dialect.name
    try:
        # Needs sqlalchemy 0.8
        if dialect != 'postgresql':
            with op.batch_alter_table('hashmap_thresholds') as batch_op:
                batch_op.drop_constraint(
                    u'uniq_field_mapping',
                    type_='unique')
                batch_op.drop_constraint(
                    u'uniq_service_mapping',
                    type_='unique')
                batch_op.create_unique_constraint(
                    'uniq_field_threshold',
                    ['level', 'field_id'])
                batch_op.create_unique_constraint(
                    'uniq_service_threshold',
                    ['level', 'service_id'])
    except AttributeError:
        # No support for batch operations
        if dialect == 'sqlite':
            new_table = create_table()
            sel = sa.sql.expression.select(new_table.columns.keys())
            op.execute(
                new_table.insert().from_select(
                    new_table.columns.keys(),
                    sel.select_from('hashmap_thresholds')))
            op.drop_table('hashmap_thresholds')
            op.rename_table('tmig_hashmap_thresholds', 'hashmap_thresholds')
        else:
            op.drop_constraint(
                u'uniq_field_mapping',
                'hashmap_thresholds',
                type_='unique')
            op.drop_constraint(
                u'uniq_service_mapping',
                'hashmap_thresholds',
                type_='unique')
            op.create_unique_constraint(
                'uniq_field_threshold',
                'hashmap_thresholds',
                ['level', 'field_id'])
            op.create_unique_constraint(
                'uniq_service_threshold',
                'hashmap_thresholds',
                ['level', 'service_id'])
