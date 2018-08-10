# -*- coding: utf-8 -*-
# Copyright 2017 Objectif Libre
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
# @author: Luka Peschke
#
from oslo_config import cfg
from oslo_db.sqlalchemy import utils
from stevedore import driver

from cloudkitty import db
from cloudkitty.storage.v1 import BaseStorage
from cloudkitty.storage.v1.hybrid import migration
from cloudkitty.storage.v1.hybrid import models
from cloudkitty import utils as ck_utils


storage_opts = [
    cfg.StrOpt(
        'backend',
        default='gnocchi',
        help='Name of the storage backend that should be used '
        'by the hybrid storage')
]

CONF = cfg.CONF
CONF.register_opts(storage_opts, group='hybrid_storage')

HYBRID_BACKENDS_NAMESPACE = 'cloudkitty.storage.hybrid.backends'


class HybridStorage(BaseStorage):
    """Hybrid Storage Backend.

    Stores dataframes in one of the available backends and other informations
    in a classical SQL database.
    """

    state_model = models.TenantState

    def __init__(self, **kwargs):
        super(HybridStorage, self).__init__(**kwargs)
        self._hybrid_backend = driver.DriverManager(
            HYBRID_BACKENDS_NAMESPACE,
            cfg.CONF.hybrid_storage.backend,
            invoke_on_load=True).driver
        self._sql_session = {}

    def _check_session(self, tenant_id):
        session = self._sql_session.get(tenant_id, None)
        if not session:
            self._sql_session[tenant_id] = db.get_session()
            self._sql_session[tenant_id].begin()

    def init(self):
        migration.upgrade('head')
        self._hybrid_backend.init()

    def get_state(self, tenant_id=None):
        session = db.get_session()
        q = utils.model_query(self.state_model, session)
        if tenant_id:
            q = q.filter(self.state_model.tenant_id == tenant_id)
        q = q.order_by(self.state_model.state.desc())
        r = q.first()
        return ck_utils.dt2ts(r.state) if r else None

    def _set_state(self, tenant_id, state):
        self._check_session(tenant_id)
        session = self._sql_session[tenant_id]
        q = utils.model_query(self.state_model, session)
        if tenant_id:
            q = q.filter(self.state_model.tenant_id == tenant_id)
        r = q.first()
        do_commit = False
        if r:
            if state > r.state:
                q.update({'state': state})
                do_commit = True
        else:
            state = self.state_model(tenant_id=tenant_id, state=state)
            session.add(state)
            do_commit = True
        if do_commit:
            session.commit()

    def _commit(self, tenant_id):
        self._hybrid_backend.commit(tenant_id, self.get_state(tenant_id))

    def _pre_commit(self, tenant_id):
        super(HybridStorage, self)._pre_commit(tenant_id)

    def _post_commit(self, tenant_id):
        self._set_state(tenant_id, self.usage_start_dt.get(tenant_id))
        super(HybridStorage, self)._post_commit(tenant_id)
        del self._sql_session[tenant_id]

    def get_total(self, begin=None, end=None, tenant_id=None,
                  service=None, groupby=None):
        return self._hybrid_backend.get_total(
            begin=begin, end=end, tenant_id=tenant_id,
            service=service, groupby=groupby)

    def _dispatch(self, data, tenant_id):
        if not self.get_state(tenant_id):
            self._set_state(tenant_id, self.usage_start_dt.get(tenant_id))
        for service in data:
            for frame in data[service]:
                self._hybrid_backend.append_time_frame(
                    service, frame, tenant_id)
                self._has_data[tenant_id] = True

    def get_tenants(self, begin, end):
        return self._hybrid_backend.get_tenants(begin, end)

    def get_time_frame(self, begin, end, **filters):
        return self._hybrid_backend.get_time_frame(begin, end, **filters)
