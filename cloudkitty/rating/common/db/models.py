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
import datetime
import sqlalchemy


class VolatileAuditableModel:

    created_at = sqlalchemy.Column(
        'created_at',
        sqlalchemy.DateTime(),
        nullable=False,
        default=datetime.datetime.now()
    )
    start = sqlalchemy.Column(
        'start',
        sqlalchemy.DateTime(),
        nullable=False,
        default=datetime.datetime.now()
    )
    end = sqlalchemy.Column(
        'end',
        sqlalchemy.DateTime(),
        nullable=True)
    name = sqlalchemy.Column(
        'name',
        sqlalchemy.String(length=32),
        nullable=False)
    description = sqlalchemy.Column(
        'description',
        sqlalchemy.String(length=256),
        nullable=True)
    deleted = sqlalchemy.Column(
        'deleted',
        sqlalchemy.DateTime(),
        nullable=True)
    created_by = sqlalchemy.Column(
        'created_by',
        sqlalchemy.String(length=32),
        nullable=False)
    updated_by = sqlalchemy.Column(
        'updated_by',
        sqlalchemy.String(length=32),
        nullable=True)
    deleted_by = sqlalchemy.Column(
        'deleted_by',
        sqlalchemy.String(length=32),
        nullable=True)
