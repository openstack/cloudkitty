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

"""Create last processed timestamp column

Revision ID: 750d3050cf71
Revises: d9d103dd4dcf
Create Date: 2021-02-08 17:00:00.000

"""
from alembic import op

import sqlalchemy
from sqlalchemy.ext import declarative

from oslo_db.sqlalchemy import models

from cloudkitty.storage_state.alembic.versions import \
    c50ed2c19204_update_storage_state_constraint as down_version_module

# revision identifiers, used by Alembic.
revision = '750d3050cf71'
down_revision = 'c50ed2c19204'
branch_labels = None
depends_on = None

Base = declarative.declarative_base()


def upgrade():
    for name, table in down_version_module.Base.metadata.tables.items():
        if name == 'cloudkitty_storage_states':
            with op.batch_alter_table(name,
                                      copy_from=table,
                                      recreate='always') as batch_op:
                batch_op.alter_column(
                    'state', new_column_name='last_processed_timestamp')

            break


class IdentifierTableForThisDataBaseModelChangeSet(Base, models.ModelBase):
    """Represents the state of a given identifier."""

    @declarative.declared_attr
    def __table_args__(cls):
        return (
            sqlalchemy.schema.UniqueConstraint(
                'identifier',
                'scope_key',
                'collector',
                'fetcher',
                name='uq_cloudkitty_storage_states_identifier'),
        )

    __tablename__ = 'cloudkitty_storage_states'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    identifier = sqlalchemy.Column(sqlalchemy.String(256),
                                   nullable=False,
                                   unique=False)
    scope_key = sqlalchemy.Column(sqlalchemy.String(40),
                                  nullable=True,
                                  unique=False)
    fetcher = sqlalchemy.Column(sqlalchemy.String(40),
                                nullable=True,
                                unique=False)
    collector = sqlalchemy.Column(sqlalchemy.String(40),
                                  nullable=True,
                                  unique=False)
    last_processed_timestamp = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False)
