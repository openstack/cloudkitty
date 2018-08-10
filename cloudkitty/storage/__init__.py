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
from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver

from cloudkitty.storage import v2 as storage_v2


LOG = logging.getLogger(__name__)


storage_opts = [
    cfg.StrOpt('backend',
               default='sqlalchemy',
               help='Name of the storage backend driver.'),
    cfg.IntOpt('version',
               min=1, max=2,
               default=1,
               help='Storage version to use.'),
]

CONF = cfg.CONF

CONF.import_opt('period', 'cloudkitty.collector', 'collect')

CONF.register_opts(storage_opts, 'storage')


class NoTimeFrame(Exception):
    """Raised when there is no time frame available."""

    def __init__(self):
        super(NoTimeFrame, self).__init__(
            "No time frame available")


def _get_storage_instance(storage_args, storage_namespace, backend=None):
    backend = backend or cfg.CONF.storage.backend
    return driver.DriverManager(
        storage_namespace,
        backend,
        invoke_on_load=True,
        invoke_kwds=storage_args
    ).driver


class V1StorageAdapter(storage_v2.BaseStorage):

    def __init__(self, storage_args, storage_namespace, backend=None):
        self.storage = _get_storage_instance(
            storage_args, storage_namespace, backend=backend)

    def init(self):
        return self.storage.init()

    def push(self, dataframes, scope_id):
        if dataframes:
            self.storage.append(dataframes, scope_id)
            self.storage.commit(scope_id)

    @staticmethod
    def _check_metric_types(metric_types):
        if isinstance(metric_types, list):
            return metric_types[0]
        return metric_types

    def retrieve(self, begin=None, end=None,
                 filters=None, group_filters=None,
                 metric_types=None,
                 offset=0, limit=100, paginate=True):
        tenant_id = group_filters.get('project_id') if group_filters else None
        metric_types = self._check_metric_types(metric_types)
        frames = self.storage.get_time_frame(
            begin, end,
            res_type=metric_types,
            tenant_id=tenant_id)

        for frame in frames:
            for _, data_list in frame['usage'].items():
                for data in data_list:
                    data['scope_id'] = (data.get('project_id')
                                        or data.get('tenant_id'))

        return {
            'total': len(frames),
            'dataframes': frames,
        }

    def total(self, groupby=None,
              begin=None, end=None,
              metric_types=None,
              filters=None, group_filters=None):
        tenant_id = group_filters.get('project_id') if group_filters else None

        storage_gby = []
        if groupby:
            for elem in set(groupby):
                if elem == 'type':
                    storage_gby.append('res_type')
                elif elem == 'project_id':
                    storage_gby.append('tenant_id')
        storage_gby = ','.join(storage_gby) if storage_gby else None
        metric_types = self._check_metric_types(metric_types)
        total = self.storage.get_total(
            begin, end,
            tenant_id=tenant_id,
            service=metric_types,
            groupby=storage_gby)

        for t in total:
            if t.get('tenant_id') is None:
                t['tenant_id'] = tenant_id
            if t.get('rate') is None:
                t['rate'] = float(0)
            if groupby and 'type' in groupby:
                t['type'] = t.get('res_type')
            else:
                t['type'] = None
        return total

    def get_tenants(self, begin, end):
        tenants = self.storage.get_tenants(begin, end)
        return tenants

    def get_state(self, tenant_id=None):
        return self.storage.get_state(tenant_id)


def get_storage(**kwargs):
    storage_args = {
        'period': CONF.collect.period,
    }
    backend = kwargs.pop('backend', None)
    storage_args.update(kwargs)

    version = kwargs.pop('version', None) or cfg.CONF.storage.version
    if int(version) > 1:
        LOG.warning('V2 Storage is not considered stable and should not be '
                    'used in production')
    storage_namespace = 'cloudkitty.storage.v{}.backends'.format(version)

    if version == 1:
        return V1StorageAdapter(
            storage_args, storage_namespace, backend=backend)
    return _get_storage_instance(
        storage_args, storage_namespace, backend=backend)
