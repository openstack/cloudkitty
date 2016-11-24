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

"""Fix unnamed constraints.

Revision ID: f8c799db4aa0
Revises: 10d2738b67df
Create Date: 2016-05-18 18:08:19.331412

"""

# revision identifiers, used by Alembic.
revision = 'f8c799db4aa0'
down_revision = '10d2738b67df'
import copy

from alembic import op
import six

from cloudkitty.rating.hash.db.sqlalchemy.alembic.models import (
    f8c799db4aa0_fix_unnamed_constraints as models)

OPS = {
    'foreignkey': {
        'hashmap_fields': [
            ('hashmap_fields_service_id_fkey',
             'fk_hashmap_fields_service_id_hashmap_services',
             {
                 'args': [
                     'hashmap_services',
                     ['service_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'CASCADE'}})],
        'hashmap_thresholds': [
            ('hashmap_thresholds_field_id_fkey',
             'fk_hashmap_thresholds_field_id_hashmap_fields',
             {
                 'args': [
                     'hashmap_fields',
                     ['field_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'CASCADE'}}),
            ('hashmap_thresholds_group_id_fkey',
             'fk_hashmap_thresholds_group_id_hashmap_groups',
             {
                 'args': [
                     'hashmap_groups',
                     ['group_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'SET NULL'}}),
            ('hashmap_thresholds_service_id_fkey',
             'fk_hashmap_thresholds_service_id_hashmap_services',
             {
                 'args': [
                     'hashmap_services',
                     ['service_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'CASCADE'}})],
        'hashmap_mappings': [
            ('hashmap_maps_field_id_fkey',
             'fk_hashmap_maps_field_id_hashmap_fields',
             {
                 'args': [
                     'hashmap_fields',
                     ['field_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'CASCADE'}}),
            ('hashmap_maps_group_id_fkey',
             'fk_hashmap_maps_group_id_hashmap_groups',
             {
                 'args': [
                     'hashmap_groups',
                     ['group_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'SET NULL'}}),
            ('hashmap_maps_service_id_fkey',
             'fk_hashmap_maps_service_id_hashmap_services',
             {
                 'args': [
                     'hashmap_fields',
                     ['field_id'],
                     ['id']],
                 'kwargs': {'ondelete': 'CASCADE'}})]
    },
    'primary': {
        'hashmap_services': [
            ('hashmap_services_pkey',
             'pk_hashmap_services',
             {'args': [['id']]})],
        'hashmap_fields': [
            ('hashmap_fields_pkey',
             'pk_hashmap_fields',
             {'args': [['id']]})],
        'hashmap_groups': [
            ('hashmap_groups_pkey',
             'pk_hashmap_groups',
             {'args': [['id']]})],
        'hashmap_mappings': [
            ('hashmap_maps_pkey',
             'pk_hashmap_maps',
             {'args': [['id']]})],
        'hashmap_thresholds': [
            ('hashmap_thresholds_pkey',
             'pk_hashmap_thresholds',
             {'args': [['id']]})]
    },
    'unique': {
        'hashmap_services': [
            ('hashmap_services_name_key',
             'uq_hashmap_services_name',
             {'args': [['name']]}),
            ('hashmap_services_service_id_key',
             'uq_hashmap_services_service_id',
             {'args': [['service_id']]})],
        'hashmap_fields': [
            ('hashmap_fields_field_id_key',
             'uq_hashmap_fields_field_id',
             {'args': [['field_id']]})],
        'hashmap_groups': [
            ('hashmap_groups_group_id_key',
             'uq_hashmap_groups_group_id',
             {'args': [['group_id']]}),
            ('hashmap_groups_name_key',
             'uq_hashmap_groups_name',
             {'args': [['name']]})],
        'hashmap_mappings': [
            ('hashmap_maps_mapping_id_key',
             'uq_hashmap_maps_mapping_id',
             {'args': [['mapping_id']]})],
        'hashmap_thresholds': [
            ('hashmap_thresholds_threshold_id_key',
             'uq_hashmap_thresholds_threshold_id',
             {'args': [['threshold_id']]})]}}

POST_OPS = {
    'primary': {
        'hashmap_mappings': [
            ('pk_hashmap_maps',
             'pk_hashmap_mappings',
             {'args': [['id']]})]
    }}


def upgrade_sqlite():
    # NOTE(sheeprine): Batch automatically recreates tables,
    # use it as a lazy way to recreate tables and transfer data automagically.
    for name, table in six.iteritems(models.Base.metadata.tables):
        with op.batch_alter_table(name, copy_from=table) as batch_op:
            # NOTE(sheeprine): Dummy operation to force recreate.
            # Easier than delete and create.
            batch_op.alter_column('id')


def upgrade_mysql():
    op.execute('SET FOREIGN_KEY_CHECKS=0;')
    tables = copy.deepcopy(models.Base.metadata.tables)
    # Copy first without constraints
    tables['hashmap_fields'].constraints = set()
    tables['hashmap_mappings'].constraints = set()
    tables['hashmap_thresholds'].constraints = set()
    for name, table in six.iteritems(tables):
        with op.batch_alter_table(name,
                                  copy_from=table,
                                  recreate='always') as batch_op:
            batch_op.alter_column('id')
    # Final copy with constraints
    for name, table in six.iteritems(models.Base.metadata.tables):
        with op.batch_alter_table(name,
                                  copy_from=table,
                                  recreate='always') as batch_op:
            batch_op.alter_column('id')
    op.execute('SET FOREIGN_KEY_CHECKS=1;')


def translate_op(op_, constraint_type, name, table, *args, **kwargs):
    if op_ == 'drop':
        op.drop_constraint(name, table, type_=constraint_type)
    else:
        if constraint_type == 'primary':
            func = op.create_primary_key
        elif constraint_type == 'unique':
            func = op.create_unique_constraint
        elif constraint_type == 'foreignkey':
            func = op.create_foreign_key
        func(name, table, *args, **kwargs)


def upgrade_postgresql():
    # NOTE(sheeprine): No automagic stuff here.
    # Check if tables need additional work
    conn = op.get_bind()
    res = conn.execute(
        "SELECT * FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS"
        " WHERE CONSTRAINT_NAME = 'hashmap_thresholds_field_id_fkey';")
    if res.rowcount:
        ops_list = [OPS, POST_OPS]
    else:
        ops_list = [POST_OPS]
    for cur_ops in ops_list:
        for constraint_type in ('foreignkey', 'unique', 'primary'):
            for table_name, constraints in six.iteritems(
                    cur_ops.get(constraint_type, dict())):
                for constraint in constraints:
                    old_name = constraint[0]
                    translate_op(
                        'drop',
                        constraint_type,
                        old_name,
                        table_name)
        for constraint_type in ('primary', 'unique', 'foreignkey'):
            for table_name, constraints in six.iteritems(
                    cur_ops.get(constraint_type, dict())):
                for constraint in constraints:
                    new_name = constraint[1]
                    params = constraint[2]
                    translate_op(
                        'create',
                        constraint_type,
                        new_name,
                        table_name,
                        *params.get('args', []),
                        **params.get('kwargs', {}))


def upgrade():
    dialect = op.get_context().dialect
    if dialect.name == 'sqlite':
        upgrade_sqlite()
    elif dialect.name == 'mysql':
        upgrade_mysql()
    elif dialect.name == 'postgresql':
        upgrade_postgresql()
