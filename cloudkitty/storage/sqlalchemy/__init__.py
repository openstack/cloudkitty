# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
# @author: Stéphane Albert
#
import json

from oslo.db.sqlalchemy import utils
import sqlalchemy

from cloudkitty import db
from cloudkitty import storage
from cloudkitty.storage.sqlalchemy import migration
from cloudkitty.storage.sqlalchemy import models
from cloudkitty import utils as ck_utils


class SQLAlchemyStorage(storage.BaseStorage):
    """SQLAlchemy Storage Backend

    """
    def __init__(self, period=3600):
        super(SQLAlchemyStorage, self).__init__(period)
        self._session = {}

    @staticmethod
    def init():
        migration.upgrade('head')

    def _pre_commit(self, tenant_id):
        self._check_session(tenant_id)
        if not self._has_data:
            empty_frame = {'vol': {'qty': 0, 'unit': 'None'},
                           'rating': {'price': 0}, 'desc': ''}
            self._append_time_frame('_NO_DATA_', empty_frame, tenant_id)

    def _commit(self, tenant_id):
        self._session[tenant_id].commit()

    def _post_commit(self, tenant_id):
        super(SQLAlchemyStorage, self)._post_commit(tenant_id)
        del self._session[tenant_id]

    def _check_session(self, tenant_id):
        session = self._session.get(tenant_id)
        if not session:
            self._session[tenant_id] = db.get_session()
            self._session[tenant_id].begin()

    def _dispatch(self, data, tenant_id):
        self._check_session(tenant_id)
        for service in data:
            for frame in data[service]:
                self._append_time_frame(service, frame, tenant_id)

    def get_state(self, tenant_id=None):
        session = db.get_session()
        q = utils.model_query(
            models.RatedDataFrame,
            session
        )
        if tenant_id:
            q = q.filter(
                models.RatedDataFrame.tenant_id == tenant_id
            )
        r = q.order_by(
            models.RatedDataFrame.begin.desc()
        ).first()
        if r:
            return ck_utils.dt2ts(r.begin)

    def get_total(self, begin=None, end=None, tenant_id=None):
        model = models.RatedDataFrame

        # Boundary calculation
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        session = db.get_session()
        q = session.query(
            sqlalchemy.func.sum(model.rate).label('rate')
        )
        if tenant_id:
            q = q.filter(
                models.RatedDataFrame.tenant_id == tenant_id
            )
        rate = q.filter(
            model.begin >= begin,
            model.end <= end
        ).scalar()
        return rate

    def get_tenants(self, begin=None, end=None):
        model = models.RatedDataFrame

        # Boundary calculation
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        session = db.get_session()
        q = utils.model_query(
            model,
            session
        ).filter(
            model.begin >= begin,
            model.end <= end
        )
        tenants = q.distinct().values(
            model.tenant_id
        )
        return [tenant.tenant_id for tenant in tenants]

    def get_time_frame(self, begin, end, **filters):
        model = models.RatedDataFrame
        session = db.get_session()
        q = utils.model_query(
            model,
            session
        ).filter(
            model.begin >= ck_utils.ts2dt(begin),
            model.end <= ck_utils.ts2dt(end)
        )
        for filter_name, filter_value in filters.items():
            if filter_value:
                q = q.filter(getattr(model, filter_name) == filter_value)
        if not filters.get('res_type'):
            q = q.filter(model.res_type != '_NO_DATA_')
        count = q.count()
        if not count:
            raise storage.NoTimeFrame()
        r = q.all()
        return [entry.to_cloudkitty() for entry in r]

    def _append_time_frame(self, res_type, frame, tenant_id):
        vol_dict = frame['vol']
        qty = vol_dict['qty']
        unit = vol_dict['unit']
        rating_dict = frame['rating']
        rate = rating_dict['price']
        desc = json.dumps(frame['desc'])
        self.add_time_frame(self.usage_start_dt.get(tenant_id),
                            self.usage_end_dt.get(tenant_id),
                            tenant_id,
                            unit,
                            qty,
                            res_type,
                            rate,
                            desc)

    def add_time_frame(self, begin, end, tenant_id, unit, qty, res_type,
                       rate, desc):
        """Create a new time frame.

        """
        frame = models.RatedDataFrame(begin=begin,
                                      end=end,
                                      tenant_id=tenant_id,
                                      unit=unit,
                                      qty=qty,
                                      res_type=res_type,
                                      rate=rate,
                                      desc=desc)
        self._session[tenant_id].add(frame)
