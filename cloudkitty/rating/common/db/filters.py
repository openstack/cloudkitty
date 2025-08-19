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
import sqlalchemy as sa


def get_filters(query, model, deleted=False, start=None, end=None,
                updated_by=None, created_by=None, deleted_by=None,
                description=None, is_active=None):

    if is_active:
        if not isinstance(is_active, bool):
            now = is_active
        else:
            now = datetime.datetime.now()
        query = query.filter(model.start <= now)
        query = query.filter(sa.or_(model.end > now, model.end == sa.null()))
        query = query.filter(model.deleted == sa.null())

    if description:
        query = query.filter(model.description.ilike(f'%{description}%'))

    if deleted_by:
        query = query.filter(model.deleted_by == deleted_by)

    if created_by:
        query = query.filter(model.created_by == created_by)

    if updated_by:
        query = query.filter(model.updated_by == updated_by)

    if not deleted:
        query = query.filter(model.deleted == sa.null())

    if start:
        query = query.filter(model.start >= start)

    if end:
        query = query.filter(model.end < end)

    return query
