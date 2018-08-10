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
# @author: Luka Peschke
#
from collections import deque
from collections import Iterable
import copy
import datetime
import decimal
import time

from gnocchiclient import auth as gauth
from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
import six

from cloudkitty.storage.v2 import BaseStorage
from cloudkitty import utils as ck_utils


LOG = log.getLogger(__name__)


CONF = cfg.CONF


gnocchi_storage_opts = [
    cfg.StrOpt(
        'gnocchi_auth_type',
        default='keystone',
        choices=['keystone', 'basic'],
        help='(v2) Gnocchi auth type (keystone or basic). Keystone '
        'credentials can be specified through the "auth_section" parameter',
    ),
    cfg.StrOpt(
        'gnocchi_user',
        default='',
        help='(v2) Gnocchi user (for basic auth only)',
    ),
    cfg.StrOpt(
        'gnocchi_endpoint',
        default='',
        help='(v2) Gnocchi endpoint (for basic auth only)',
    ),
    cfg.StrOpt(
        'api_interface',
        default='internalURL',
        help='(v2) Endpoint URL type (for keystone auth only)',
    ),
    cfg.IntOpt(
        'measure_chunk_size',
        min=10, max=1000000,
        default=500,
        help='(v2) Maximum amount of measures to send to gnocchi at once '
        '(defaults to 500).',
    ),
]


CONF.register_opts(gnocchi_storage_opts, 'storage_gnocchi')
ks_loading.register_session_conf_options(CONF, 'storage_gnocchi')
ks_loading.register_auth_conf_options(CONF, 'storage_gnocchi')


RESOURCE_TYPE_NAME_ROOT = 'cloudkitty_metric_'
ARCHIVE_POLICY_NAME = 'cloudkitty_archive_policy'

GROUPBY_NAME_ROOT = 'groupby_attr_'
META_NAME_ROOT = 'meta_attr_'


class GnocchiResource(object):
    """Class representing a gnocchi resource

    It provides utils for resource_type/resource creation and identifying.
    """

    def __init__(self, name, metric, conn, scope_id):
        """Resource_type name, metric, gnocchiclient"""

        self.name = name
        self.resource_type = RESOURCE_TYPE_NAME_ROOT + name
        self.unit = metric['vol']['unit']
        self.groupby = {
            k: v if v else '' for k, v in metric['groupby'].items()}
        self.groupby['ck_scope_id'] = scope_id
        self.metadata = {
            k: v if v else '' for k, v in metric['metadata'].items()}
        self._trans_groupby = {
            GROUPBY_NAME_ROOT + key: val for key, val in self.groupby.items()
        }
        self._trans_metadata = {
            META_NAME_ROOT + key: val for key, val in self.metadata.items()
        }
        self._conn = conn
        self._resource = None
        self.attributes = self.metadata.copy()
        self.attributes.update(self.groupby)
        self._trans_attributes = self._trans_metadata.copy()
        self._trans_attributes.update(self._trans_groupby)
        self.needs_update = False

    def __getitem__(self, key):
        output = self._trans_attributes.get(GROUPBY_NAME_ROOT + key, None)
        if output is None:
            output = self._trans_attributes.get(META_NAME_ROOT + key, None)
        return output

    def __eq__(self, other):
        if self.resource_type != other.resource_type or \
           self['id'] != other['id']:
            return False
        own_keys = list(self.groupby.keys())
        own_keys.sort()
        other_keys = list(other.groupby.keys())
        other_keys.sort()
        if own_keys != other_keys:
            return False

        for key in own_keys:
            if other[key] != self[key]:
                return False

        return True

    @property
    def qty(self):
        if self._resource:
            return self._resource['metrics']['qty']
        return None

    @property
    def cost(self):
        if self._resource:
            return self._resource['metrics']['cost']
        return None

    def _get_res_type_dict(self):
        attributes = {}
        for key in self._trans_groupby.keys():
            attributes[key] = {'required': True, 'type': 'string'}
        attributes['unit'] = {'required': True, 'type': 'string'}
        for key in self._trans_metadata.keys():
            attributes[key] = {'required': False, 'type': 'string'}

        return {
            'name': self.resource_type,
            'attributes': attributes,
        }

    def create_resource_type(self):
        """Allows to create the type corresponding to this resource."""
        try:
            self._conn.resource_type.get(self.resource_type)
        except gexceptions.ResourceTypeNotFound:
            res_type = self._get_res_type_dict()
            LOG.debug('Creating resource_type {} in gnocchi'.format(
                self.resource_type))
            self._conn.resource_type.create(res_type)

    @staticmethod
    def _get_rfc6902_attributes_add_op(new_attributes):
        return [{
            'op': 'add',
            'path': '/attributes/{}'.format(attr),
            'value': {
                'required': attr.startswith(GROUPBY_NAME_ROOT),
                'type': 'string'
            }
        } for attr in new_attributes]

    def update_resource_type(self):
        needed_res_type = self._get_res_type_dict()
        current_res_type = self._conn.resource_type.get(
            needed_res_type['name'])

        new_attributes = [attr for attr in needed_res_type['attributes'].keys()
                          if attr not in current_res_type['attributes'].keys()]
        if not new_attributes:
            return
        LOG.info('Adding {} to resource_type {}'.format(
            [attr.replace(GROUPBY_NAME_ROOT, '').replace(META_NAME_ROOT, '')
             for attr in new_attributes],
            current_res_type['name'].replace(RESOURCE_TYPE_NAME_ROOT, ''),
        ))
        new_attributes_op = self._get_rfc6902_attributes_add_op(new_attributes)
        self._conn.resource_type.update(
            needed_res_type['name'], new_attributes_op)

    def _create_metrics(self):
        qty = self._conn.metric.create(
            name='qty',
            unit=self.unit,
            archive_policy_name=ARCHIVE_POLICY_NAME,
        )
        cost = self._conn.metric.create(
            name='cost',
            archive_policy_name=ARCHIVE_POLICY_NAME,
        )
        return qty, cost

    def exists_in_gnocchi(self):
        """Check if the resource exists in gnocchi.

        Returns true if the resource exists.
        """
        query = {
            'and': [
                {'=': {key: value}}
                for key, value in self._trans_groupby.items()
            ],
        }
        res = self._conn.resource.search(resource_type=self.resource_type,
                                         query=query)
        if len(res) > 1:
            LOG.warning(
                "Found more than one metric matching groupby. This may not "
                "have the behavior you're expecting. You should probably add "
                "some items to groupby")
        if len(res) > 0:
            self._resource = res[0]
            return True
        return False

    def create(self):
        """Creates the resource in gnocchi."""
        if self._resource:
            return
        self.create_resource_type()
        qty_metric, cost_metric = self._create_metrics()
        resource = self._trans_attributes.copy()
        resource['metrics'] = {
            'qty': qty_metric['id'],
            'cost': cost_metric['id'],
        }
        resource['id'] = uuidutils.generate_uuid()
        resource['unit'] = self.unit
        if not self.exists_in_gnocchi():
            try:
                self._resource = self._conn.resource.create(
                    self.resource_type, resource)
            # Attributes have changed
            except gexceptions.BadRequest:
                self.update_resource_type()
                self._resource = self._conn.resource.create(
                    self.resource_type, resource)

    def update(self, metric):
        for key, val in metric['metadata'].items():
            self._resource[META_NAME_ROOT + key] = val
        self._resource = self._conn.update(
            self.resource_type, self._resource['id'], self._resource)
        self.needs_update = False
        return self._resource


class GnocchiResourceCacher(object):
    """Class allowing to keep created resource in memory to improve perfs.

    It keeps the last max_size resources in cache.
    """

    def __init__(self, max_size=500):
        self._resources = deque(maxlen=max_size)

    def __contains__(self, resource):
        for r in self._resources:
            if r == resource:
                for key, val in resource.metadata.items():
                    if val != r[key]:
                        r.needs_update = True
                return True
        return False

    def add_resource(self, resource):
        """Add a resource to the cacher.

        :param resource: resource to add
        :type resource: GnocchiResource
        """
        for r in self._resources:
            if r == resource:
                return
        self._resources.append(resource)

    def get(self, resource):
        """Returns the resource matching to the parameter.

        :param resource: resource to get
        :type resource: GnocchiResource
        """
        for r in self._resources:
            if r == resource:
                return r
        return None

    def get_by_id(self, resource_id):
        """Returns the resource matching the given id.

        :param resource_id: ID of the resource to get
        :type resource: str
        """
        for r in self._resources:
            if r['id'] == resource_id:
                return r
        return None


class GnocchiStorage(BaseStorage):

    default_op = ['aggregate', 'sum', ['metric', 'cost', 'sum'], ]

    def _check_archive_policy(self):
        try:
            self._conn.archive_policy.get(ARCHIVE_POLICY_NAME)
        except gexceptions.ArchivePolicyNotFound:
            definition = [
                {'granularity': str(CONF.collect.period) + 's',
                 'timespan': '{d} days'.format(d=self.get_retention().days)},
            ]
            archive_policy = {
                'name': ARCHIVE_POLICY_NAME,
                'back_window': 0,
                'aggregation_methods': [
                    'std', 'count', 'min', 'max', 'sum', 'mean'],
                'definition': definition,
            }
            self._conn.archive_policy.create(archive_policy)

    def __init__(self, *args, **kwargs):
        super(GnocchiStorage, self).__init__(*args, **kwargs)

        adapter_options = {'connect_retries': 3}
        if CONF.storage_gnocchi.gnocchi_auth_type == 'keystone':
            auth_plugin = ks_loading.load_auth_from_conf_options(
                CONF,
                'storage_gnocchi',
            )
            adapter_options['interface'] = CONF.storage_gnocchi.api_interface
        else:
            auth_plugin = gauth.GnocchiBasicPlugin(
                user=CONF.storage_gnocchi.gnocchi_user,
                endpoint=CONF.storage_gnocchi.gnocchi_endpoint,
            )
        self._conn = gclient.Client(
            '1',
            session_options={'auth': auth_plugin},
            adapter_options=adapter_options,
        )
        self._cacher = GnocchiResourceCacher()

    def init(self):
        self._check_archive_policy()

    def _check_resource(self, metric_name, metric, scope_id):
        resource = GnocchiResource(metric_name, metric, self._conn, scope_id)
        if resource in self._cacher:
            return self._cacher.get(resource)
        resource.create()
        self._cacher.add_resource(resource)
        return resource

    def _push_measures_to_gnocchi(self, measures):
        if measures:
            try:
                self._conn.metric.batch_metrics_measures(measures)
            except gexceptions.BadRequest:
                LOG.warning(
                    'An exception occured while trying to push measures to '
                    'gnocchi. Retrying in 1 second. If this happens again, '
                    'set measure_chunk_size to a lower value.')
                time.sleep(1)
                self._conn.metric.batch_metrics_measures(measures)

    def push(self, dataframes, scope_id):
        if not isinstance(dataframes, list):
            dataframes = [dataframes]
        measures = {}
        nb_measures = 0
        for dataframe in dataframes:
            timestamp = dataframe['period']['begin']
            for metric_name, metrics in dataframe['usage'].items():
                for metric in metrics:
                    resource = self._check_resource(
                        metric_name, metric, scope_id)
                    if resource.needs_update:
                        resource.update(metric)
                    if not resource.qty or not resource.cost:
                        LOG.warning('Unexpected continue')
                        continue

                    # resource.qty is the uuid of the qty metric
                    if not measures.get(resource.qty):
                        measures[resource.qty] = []
                    measures[resource.qty].append({
                        'timestamp': timestamp,
                        'value': metric['vol']['qty'],
                    })

                    if not measures.get(resource.cost):
                        measures[resource.cost] = []
                    measures[resource.cost].append({
                        'timestamp': timestamp,
                        'value': metric['rating']['price'],
                    })
                    nb_measures += 2
                    if nb_measures >= CONF.storage_gnocchi.measure_chunk_size:
                        LOG.debug('Pushing {} measures to gnocchi.'.format(
                            nb_measures))
                        self._push_measures_to_gnocchi(measures)
                        measures = {}
                        nb_measures = 0

        LOG.debug('Pushing {} measures to gnocchi.'.format(nb_measures))
        self._push_measures_to_gnocchi(measures)

    def _get_ck_resource_types(self):
        types = self._conn.resource_type.list()
        return [gtype['name'] for gtype in types
                if gtype['name'].startswith(RESOURCE_TYPE_NAME_ROOT)]

    def _check_res_types(self, res_type=None):
        if res_type is None:
            output = self._get_ck_resource_types()
        elif isinstance(res_type, Iterable):
            output = res_type
        else:
            output = [res_type]
        return sorted(output)

    @staticmethod
    def _check_begin_end(begin, end):
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()
        if isinstance(begin, six.text_type):
            begin = ck_utils.iso2dt(begin)
        if isinstance(begin, int):
            begin = ck_utils.ts2dt(begin)
        if isinstance(end, six.text_type):
            end = ck_utils.iso2dt(end)
        if isinstance(end, int):
            end = ck_utils.ts2dt(end)

        return begin, end

    def _get_resource_frame(self,
                            cost_measure,
                            qty_measure,
                            resource,
                            scope_id):
        # Getting price
        price = decimal.Decimal(cost_measure[2])
        price_dict = {'price': float(price)}

        # Getting vol
        vol_dict = {
            'qty': decimal.Decimal(qty_measure[2]),
            'unit': resource.get('unit'),
        }

        # Formatting
        groupby = {
            k.replace(GROUPBY_NAME_ROOT, ''): v
            for k, v in resource.items() if k.startswith(GROUPBY_NAME_ROOT)
        }
        metadata = {
            k.replace(META_NAME_ROOT, ''): v
            for k, v in resource.items() if k.startswith(META_NAME_ROOT)
        }
        return {
            'groupby': groupby,
            'metadata': metadata,
            'vol': vol_dict,
            'rating': price_dict,
            'scope_id': scope_id,
        }

    def _to_cloudkitty(self,
                       scope_id,
                       res_type,
                       resource,
                       cost_measure,
                       qty_measure):

        start = cost_measure[0]
        stop = start + datetime.timedelta(seconds=cost_measure[1])

        # Period
        period_dict = {
            'begin': ck_utils.dt2iso(start),
            'end': ck_utils.dt2iso(stop),
        }

        return {
            'usage': {res_type: [
                self._get_resource_frame(
                    cost_measure, qty_measure, resource, scope_id)]
            },
            'period': period_dict,
        }

    def _get_resource_info(self, resource_ids, start, stop):
        search = {
            'and': [
                {
                    'or': [
                        {
                            '=': {'id': resource_id},
                        }
                        for resource_id in resource_ids
                    ],
                },
            ],
        }

        resources = []
        marker = None
        while True:
            resource_chunk = self._conn.resource.search(query=search,
                                                        details=True,
                                                        marker=marker,
                                                        sorts=['id:asc'])
            if len(resource_chunk) < 1:
                break
            marker = resource_chunk[-1]['id']
            resources += resource_chunk
        return {resource['id']: resource for resource in resources}

    @staticmethod
    def _dataframes_to_list(dataframes):
        keys = sorted(dataframes.keys())
        return [dataframes[key] for key in keys]

    def _get_dataframes(self, measures, resource_info):
        dataframes = {}

        for measure in measures:
            resource_type = measure['group']['type']
            resource_id = measure['group']['id']

            # Raw metrics do not contain all required attributes
            resource = resource_info[resource_id]
            scope_id = resource[GROUPBY_NAME_ROOT + 'ck_scope_id']

            dataframe = dataframes.get(measure['cost'][0])
            ck_resource_type_name = resource_type.replace(
                RESOURCE_TYPE_NAME_ROOT, '')
            if dataframe is None:
                dataframes[measure['cost'][0]] = self._to_cloudkitty(
                    scope_id,
                    ck_resource_type_name,
                    resource,
                    measure['cost'],
                    measure['qty'])
            elif dataframe['usage'].get(ck_resource_type_name) is None:
                dataframe['usage'][ck_resource_type_name] = [
                    self._get_resource_frame(
                        measure['cost'], measure['qty'], resource, scope_id)]
            else:
                dataframe['usage'][ck_resource_type_name].append(
                    self._get_resource_frame(
                        measure['cost'], measure['qty'], resource, scope_id))
        return self._dataframes_to_list(dataframes)

    @staticmethod
    def _create_filters(filters, group_filters):
        output = {}

        if filters:
            for k, v in filters.items():
                output[META_NAME_ROOT + k] = v
        if group_filters:
            for k, v in group_filters.items():
                output[GROUPBY_NAME_ROOT + k] = v
        return output

    def _raw_metrics_to_distinct_measures(self,
                                          raw_cost_metrics,
                                          raw_qty_metrics):
        output = []
        for cost, qty in zip(raw_cost_metrics, raw_qty_metrics):
            output += [{
                'cost': cost_measure,
                'qty': qty['measures']['measures']['aggregated'][idx],
                'group': cost['group'],
            } for idx, cost_measure in enumerate(
                cost['measures']['measures']['aggregated'])
            ]
        # Sorting by timestamp, metric type and resource ID
        output.sort(key=lambda x: (
            x['cost'][0], x['group']['type'], x['group']['id']))
        return output

    def retrieve(self, begin=None, end=None,
                 filters=None, group_filters=None,
                 metric_types=None,
                 offset=0, limit=100, paginate=True):

        begin, end = self._check_begin_end(begin, end)

        metric_types = self._check_res_types(metric_types)

        # Getting a list of active gnocchi resources with measures
        filters = self._create_filters(filters, group_filters)

        # FIXME(lukapeschke): We query all resource types in order to get the
        # total amount of dataframes, but this could be done in a better way;
        # ie. by not doing addtional queries once the limit is reached
        raw_cost_metrics = []
        raw_qty_metrics = []
        for mtype in metric_types:
            cost_metrics, qty_metrics = self._single_resource_type_aggregates(
                begin, end, mtype, ['type', 'id'], filters, fetch_qty=True)
            raw_cost_metrics += cost_metrics
            raw_qty_metrics += qty_metrics
        measures = self._raw_metrics_to_distinct_measures(
            raw_cost_metrics, raw_qty_metrics)

        result = {'total': len(measures)}

        if paginate:
            measures = measures[offset:limit]
        if len(measures) < 1:
            return {
                'total': 0,
                'dataframes': [],
            }
        resource_ids = [measure['group']['id'] for measure in measures]

        resource_info = self._get_resource_info(resource_ids, begin, end)

        result['dataframes'] = self._get_dataframes(measures, resource_info)
        return result

    def _single_resource_type_aggregates(self,
                                         start, stop,
                                         metric_type,
                                         groupby,
                                         filters,
                                         fetch_qty=False):
        search = {
            'and': [
                {'=': {'type': metric_type}}
            ]
        }
        search['and'] += [{'=': {k: v}} for k, v in filters.items()]

        cost_op = self.default_op
        output = (
            self._conn.aggregates.fetch(
                cost_op,
                search=search,
                groupby=groupby,
                resource_type=metric_type,
                start=start, stop=stop),
            None
        )
        if fetch_qty:
            qty_op = copy.deepcopy(self.default_op)
            qty_op[2][1] = 'qty'
            output = (
                output[0],
                self._conn.aggregates.fetch(
                    qty_op,
                    search=search,
                    groupby=groupby,
                    resource_type=metric_type,
                    start=start, stop=stop)
            )
        return output

    @staticmethod
    def _ungroup_type(rated_resources):
        output = []
        for rated_resource in rated_resources:
            rated_resource['group'].pop('type', None)
            new_item = True
            for elem in output:
                if rated_resource['group'] == elem['group']:
                    elem['measures']['measures']['aggregated'] \
                        += rated_resource['measures']['measures']['aggregated']
                    new_item = False
                    break
            if new_item:
                output.append(rated_resource)
        return output

    def total(self, groupby=None,
              begin=None, end=None,
              metric_types=None,
              filters=None, group_filters=None):
        begin, end = self._check_begin_end(begin, end)

        if groupby is None:
            groupby = []
        request_groupby = [
            GROUPBY_NAME_ROOT + elem for elem in groupby if elem != 'type']
        # We need to have a least one attribute on which to group
        request_groupby.append('type')

        # NOTE(lukapeschke): For now, it isn't possible to group aggregates
        # from different resource types using custom attributes, so we need
        # to do one request per resource type.
        rated_resources = []
        metric_types = self._check_res_types(metric_types)
        filters = self._create_filters(filters, group_filters)
        for mtype in metric_types:
            resources, _ = self._single_resource_type_aggregates(
                begin, end, mtype, request_groupby, filters)

            for resource in resources:
                # If we have found something
                if len(resource['measures']['measures']['aggregated']):
                    rated_resources.append(resource)

        # NOTE(lukapeschke): We undo what has been done previously (grouping
        # per type). This is not performant. Should be fixed as soon as
        # previous note is supported in gnocchi
        if 'type' not in groupby:
            rated_resources = self._ungroup_type(rated_resources)

        output = []
        for rated_resource in rated_resources:
            rate = sum(measure[2] for measure in
                       rated_resource['measures']['measures']['aggregated'])
            output_elem = {
                'begin': begin,
                'end': end,
                'rate': rate,
            }
            for group in groupby:
                output_elem[group] = rated_resource['group'].get(
                    GROUPBY_NAME_ROOT + group, '')
            # If we want to group per type
            if 'type' in groupby:
                output_elem['type'] = rated_resource['group'].get(
                    'type', '').replace(RESOURCE_TYPE_NAME_ROOT, '') or ''
            output.append(output_elem)
        return output
