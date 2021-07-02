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
from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


def to_string_selected_fields(object_to_print, fields=[]):
    object_to_return = {}
    if object_to_print:
        object_to_return = {
            a: y for a, y in object_to_print.items() if a in fields}
    return str(object_to_return)


class IdentifierState(Base, models.ModelBase):
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
    scope_activation_toggle_date = sqlalchemy.Column(
        'scope_activation_toggle_date', sqlalchemy.DateTime, nullable=False,
        server_default=sqlalchemy.sql.func.now())
    active = sqlalchemy.Column('active', sqlalchemy.Boolean, nullable=False,
                               default=True)

    def __str__(self):
        return to_string_selected_fields(
            self, ['id', 'identifier', 'state', 'active'])


class ReprocessingScheduler(Base, models.ModelBase):
    """Represents the reprocessing scheduler table."""

    @declarative.declared_attr
    def __table_args__(cls):
        return (
            sqlalchemy.schema.PrimaryKeyConstraint('id'),
        )

    __tablename__ = 'storage_scope_reprocessing_schedule'

    id = sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True)
    reason = sqlalchemy.Column("reason", sqlalchemy.Text, nullable=False)

    identifier = sqlalchemy.Column("identifier", sqlalchemy.String(256),
                                   nullable=False, unique=False)
    start_reprocess_time = sqlalchemy.Column("start_reprocess_time",
                                             sqlalchemy.DateTime,
                                             nullable=False)
    end_reprocess_time = sqlalchemy.Column("end_reprocess_time",
                                           sqlalchemy.DateTime,
                                           nullable=False)
    current_reprocess_time = sqlalchemy.Column("current_reprocess_time",
                                               sqlalchemy.DateTime,
                                               nullable=True)

    def __str__(self):
        return to_string_selected_fields(
            self, ['id', 'identifier', 'start_reprocess_time',
                   'end_reprocess_time', 'current_reprocess_time'])
