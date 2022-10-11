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
import functools

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver

from cloudkitty import dataframe
from cloudkitty.storage import v2 as storage_v2
from cloudkitty.utils import tz as tzutils

LOG = logging.getLogger(__name__)


storage_opts = [
    cfg.StrOpt('backend',
               default='influxdb',
               help='Name of the storage backend driver.'),
    cfg.IntOpt('version',
               min=1, max=2,
               default=2,
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
        self._localize_dataframes = functools.partial(
            self.__update_frames_timestamps, tzutils.utc_to_local)
        self._make_dataframes_naive = functools.partial(
            self.__update_frames_timestamps, tzutils.local_to_utc, naive=True)

    def init(self):
        return self.storage.init()

    @staticmethod
    def __update_frames_timestamps(func, frames, **kwargs):
        for frame in frames:
            start = frame.start
            end = frame.end
            if start:
                frame.start = func(start, **kwargs)
            if end:
                frame.end = func(end, **kwargs)

    def push(self, dataframes, scope_id=None):
        if dataframes:
            self._make_dataframes_naive(dataframes)
            self.storage.append(
                [d.as_dict(mutable=True, legacy=True) for d in dataframes],
                scope_id)
            self.storage.commit(scope_id)

    @staticmethod
    def _check_metric_types(metric_types):
        if isinstance(metric_types, list):
            return metric_types[0]
        return metric_types

    def retrieve(self, begin=None, end=None,
                 filters=None,
                 metric_types=None,
                 offset=0, limit=100, paginate=True):
        tenant_id = filters.get('project_id') if filters else None
        metric_types = self._check_metric_types(metric_types)
        frames = self.storage.get_time_frame(
            tzutils.local_to_utc(begin, naive=True) if begin else None,
            tzutils.local_to_utc(end, naive=True) if end else None,
            res_type=metric_types,
            tenant_id=tenant_id)
        frames = [dataframe.DataFrame.from_dict(frame, legacy=True)
                  for frame in frames]
        self._localize_dataframes(frames)
        return {
            'total': len(frames),
            'dataframes': frames,
        }

    @staticmethod
    def _localize_total(iterable):
        for elem in iterable:
            begin = elem['begin']
            end = elem['end']
            if begin:
                elem['begin'] = tzutils.utc_to_local(begin)
            if end:
                elem['end'] = tzutils.utc_to_local(end)

    def total(self, **arguments):
        filters = arguments.pop('filters', None)
        if filters:
            tenant_id = filters.get('project_id')

            arguments['tenant_id'] = tenant_id
        else:
            tenant_id = None

        groupby = arguments.get('groupby')
        storage_gby = self.get_storage_groupby(groupby)

        metric_types = arguments.pop('metric_types', None)
        if metric_types:
            metric_types = self._check_metric_types(metric_types)
            arguments['service'] = metric_types

        arguments['begin'] = tzutils.local_to_utc(
            arguments['begin'], naive=True)
        arguments['end'] = tzutils.local_to_utc(
            arguments['end'], naive=True)

        arguments['groupby'] = storage_gby

        total = self.storage.get_total(**arguments)

        for t in total:
            if t.get('tenant_id') is None:
                t['tenant_id'] = tenant_id
            if t.get('rate') is None:
                t['rate'] = float(0)
            if groupby and 'type' in groupby:
                t['type'] = t.get('res_type')
            else:
                t['type'] = None
        self._localize_total(total)
        return {
            'total': len(total),
            'results': total,
        }

    @staticmethod
    def get_storage_groupby(groupby):
        storage_gby = []
        if groupby:
            for elem in set(groupby):
                if elem == 'type':
                    storage_gby.append('res_type')
                elif elem == 'project_id':
                    storage_gby.append('tenant_id')
                else:
                    LOG.warning("The groupby [%s] is not supported by MySQL "
                                "storage backend.", elem)
        return ','.join(storage_gby) if storage_gby else None

    def get_tenants(self, begin, end):
        return self.storage.get_tenants(begin, end)

    def get_state(self, tenant_id=None):
        return self.storage.get_state(tenant_id)

    def delete(self, begin=None, end=None, filters=None):
        LOG.warning('Calling unsupported "delete" method on v1 storage.')


def get_storage(**kwargs):
    storage_args = {
        'period': CONF.collect.period,
    }
    backend = kwargs.pop('backend', None)
    storage_args.update(kwargs)

    version = kwargs.pop('version', None) or cfg.CONF.storage.version
    if int(version) > 1:
        LOG.warning('V2 Storage is in beta. Its API is considered stable but '
                    'its implementation may still evolve.')
    storage_namespace = 'cloudkitty.storage.v{}.backends'.format(version)

    if version == 1:
        return V1StorageAdapter(
            storage_args, storage_namespace, backend=backend)
    return _get_storage_instance(
        storage_args, storage_namespace, backend=backend)
