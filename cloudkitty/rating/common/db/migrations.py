# -*- coding: utf-8 -*-
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
import sqlalchemy as sa


def create_common_tables(batch_op):
    batch_op.add_column(
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.sql.func.now()
        ))
    batch_op.add_column(
        sa.Column(
            'start',
            sa.DateTime(),
            nullable=False,
            server_default=sa.sql.func.now()
        ))
    batch_op.add_column(
        sa.Column(
            'end',
            sa.DateTime(),
            nullable=True))

    batch_op.add_column(
        sa.Column(
            'description',
            sa.Text(length=256),
            nullable=True))
    batch_op.add_column(
        sa.Column(
            'deleted',
            sa.DateTime(),
            nullable=True))
    batch_op.add_column(
        sa.Column(
            'created_by',
            sa.String(length=32),
            nullable=False))
    batch_op.add_column(
        sa.Column(
            'updated_by',
            sa.String(length=32),
            nullable=True))
    batch_op.add_column(
        sa.Column(
            'deleted_by',
            sa.String(length=32),
            nullable=True))
