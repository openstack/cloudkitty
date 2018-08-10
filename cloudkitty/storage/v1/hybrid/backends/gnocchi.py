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
import datetime
import decimal
import json

from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
import six

from cloudkitty.collector import validate_conf
from cloudkitty.storage.v1.hybrid.backends import BaseHybridBackend
import cloudkitty.utils as ck_utils


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

CONF.import_opt('period', 'cloudkitty.collector', 'collect')

GNOCCHI_STORAGE_OPTS = 'storage_gnocchi'
gnocchi_storage_opts = [
    cfg.StrOpt('interface',
               default='internalURL',
               help='endpoint url type'),
    cfg.StrOpt('archive_policy_name',
               default='rating',
               help='Gnocchi storage archive policy name.'),
    # The archive policy definition MUST include the collect period granularity
    cfg.StrOpt('archive_policy_definition',
               default='[{"granularity": '
                       + six.text_type(CONF.collect.period) +
                       ', "timespan": "90 days"}, '
                       '{"granularity": 86400, "timespan": "360 days"}, '
                       '{"granularity": 2592000, "timespan": "1800 days"}]',
               help='Gnocchi storage archive policy definition.'), ]
CONF.register_opts(gnocchi_storage_opts, GNOCCHI_STORAGE_OPTS)

ks_loading.register_session_conf_options(
    CONF,
    GNOCCHI_STORAGE_OPTS)
ks_loading.register_auth_conf_options(
    CONF,
    GNOCCHI_STORAGE_OPTS)

RESOURCE_TYPE_NAME_ROOT = 'rating_service_'
METADATA_NAME_ROOT = 'ckmeta_'


class DecimalJSONEncoder(json.JSONEncoder):
    """Wrapper class to handle decimal.Decimal objects in json.dumps()."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalJSONEncoder, self).default(obj)


class UnknownResourceType(Exception):
    """Exception raised when an unknown resource type is encountered"""

    def __init__(self, resource_type):
        super(UnknownResourceType, self).__init__(
            'Unknown resource type {}'.format(resource_type)
        )


class GnocchiStorage(BaseHybridBackend):
    """Gnocchi backend for hybrid storage.

    """

    groupby_keys = ['res_type', 'tenant_id']
    groupby_values = ['type', 'project_id']

    def _init_resource_types(self):
        for metric_name, metric in self.conf.items():
            metric_dict = dict()
            metric_dict['attributes'] = list()
            for attribute in metric.get('metadata', {}):
                metric_dict['attributes'].append(
                    METADATA_NAME_ROOT + attribute)
            metric_dict['required_attributes'] = ['unit', 'resource_id']
            for attribute in metric['groupby']:
                metric_dict['required_attributes'].append(
                    METADATA_NAME_ROOT + attribute)

            metric_dict['name'] = RESOURCE_TYPE_NAME_ROOT + metric['alt_name']
            if metric['mutate'] == 'NUMBOOL':
                metric_dict['qty_metric'] = 1
            else:
                metric_dict['qty_metric'] = metric_name
            self._resource_type_data[metric['alt_name']] = metric_dict

    def _get_res_type_dict(self, res_type):
        res_type_data = self._resource_type_data.get(res_type, None)
        if not res_type_data:
            return None
        attribute_dict = dict()
        for attribute in res_type_data['attributes']:
            attribute_dict[attribute] = {
                'required': False,
                'type': 'string',
            }
        for attribute in res_type_data['required_attributes']:
            attribute_dict[attribute] = {
                'required': True,
                'type': 'string',
            }
        return {
            'name': res_type_data['name'],
            'attributes': attribute_dict,
        }

    def _create_resource(self, res_type, tenant_id, data):
        res_type_data = self._resource_type_data.get(res_type, None)
        if not res_type_data:
            raise UnknownResourceType(
                "Unknown resource type '{}'".format(res_type))

        res_dict = {
            'id': data['id'],
            'resource_id': data['id'],
            'project_id': tenant_id,
            'user_id': 'cloudkitty',
            'unit': data['unit'],
        }
        for key in ['attributes', 'required_attributes']:
            for attr in res_type_data[key]:
                if METADATA_NAME_ROOT in attr:
                    res_dict[attr] = data.get(
                        attr.replace(METADATA_NAME_ROOT, ''), None) or ''
                    if isinstance(res_dict[attr], decimal.Decimal):
                        res_dict[attr] = float(res_dict[attr])

        created_metrics = [
            self._conn.metric.create({
                'name': metric,
                'archive_policy_name':
                    CONF.storage_gnocchi.archive_policy_name,
            }) for metric in ['price', res_type]
        ]

        metrics_dict = dict()
        for metric in created_metrics:
            metrics_dict[metric['name']] = metric['id']
        res_dict['metrics'] = metrics_dict
        try:
            return self._conn.resource.create(res_type_data['name'], res_dict)
        except gexceptions.ResourceAlreadyExists:
            res_dict['id'] = uuidutils.generate_uuid()
            return self._conn.resource.create(res_type_data['name'], res_dict)

    def _get_resource(self, resource_type, resource_id):
        try:
            resource_name = self._resource_type_data[resource_type]['name']
        except KeyError:
            raise UnknownResourceType(
                "Unknown resource type '{}'".format(resource_type))
        try:
            return self._conn.resource.get(resource_name, resource_id)
        except gexceptions.ResourceNotFound:
            return None

    def _find_resource(self, resource_type, resource_id):
        try:
            resource_type = self._resource_type_data[resource_type]['name']
        except KeyError:
            raise UnknownResourceType(
                "Unknown resource type '{}'".format(resource_type))
        query = {
            '=': {
                'resource_id': resource_id,
            }
        }
        try:
            return self._conn.resource.search(
                resource_type=resource_type, query=query, limit=1)[0]
        except IndexError:
            return None

    def _create_resource_type(self, resource_type):
        res_type = self._resource_type_data.get(resource_type, None)
        if not res_type:
            return None
        res_type_dict = self._get_res_type_dict(resource_type)
        try:
            output = self._conn.resource_type.create(res_type_dict)
        except gexceptions.ResourceTypeAlreadyExists:
            output = None
        return output

    def _get_resource_type(self, resource_type):
        res_type = self._resource_type_data.get(resource_type, None)
        if not res_type:
            return None
        return self._conn.resource_type.get(res_type['name'])

    def __init__(self, **kwargs):
        super(GnocchiStorage, self).__init__(**kwargs)
        conf = kwargs.get('conf') or ck_utils.load_conf(
            CONF.collect.metrics_conf)
        self.conf = validate_conf(conf)
        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            GNOCCHI_STORAGE_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            GNOCCHI_STORAGE_OPTS,
            auth=self.auth)
        self._conn = gclient.Client(
            '1',
            session=self.session,
            adapter_options={'connect_retries': 3,
                             'interface': CONF.storage_gnocchi.interface})
        self._archive_policy_name = (
            CONF.storage_gnocchi.archive_policy_name)
        self._archive_policy_definition = json.loads(
            CONF.storage_gnocchi.archive_policy_definition)
        self._period = kwargs.get('period') or CONF.collect.period
        self._measurements = dict()
        self._resource_type_data = dict()
        self._init_resource_types()

    def commit(self, tenant_id, state):
        if not self._measurements.get(tenant_id, None):
            return
        commitable_measurements = dict()
        for metrics in self._measurements[tenant_id].values():
            for metric_id, measurements in metrics.items():
                if measurements:
                    measures = list()
                    for measurement in measurements:
                        measures.append(
                            {
                                'timestamp': state,
                                'value': measurement,
                            }
                        )
                    commitable_measurements[metric_id] = measures
        if commitable_measurements:
            self._conn.metric.batch_metrics_measures(commitable_measurements)
        del self._measurements[tenant_id]

    def init(self):
        try:
            self._conn.archive_policy.get(self._archive_policy_name)
        except gexceptions.ArchivePolicyNotFound:
            ck_archive_policy = {}
            ck_archive_policy['name'] = self._archive_policy_name
            ck_archive_policy['back_window'] = 0
            ck_archive_policy['aggregation_methods'] \
                = ['std', 'count', 'min', 'max', 'sum', 'mean']
            ck_archive_policy['definition'] = self._archive_policy_definition
            self._conn.archive_policy.create(ck_archive_policy)
        for service in self._resource_type_data.keys():
            try:
                self._get_resource_type(service)
            except gexceptions.ResourceTypeNotFound:
                self._create_resource_type(service)

    def get_total(self, begin=None, end=None, tenant_id=None,
                  service=None, groupby=None):
        # Query can't be None if we don't specify a resource_id
        query = {'and': [{
            'like': {'type': RESOURCE_TYPE_NAME_ROOT + '%'},
        }]}
        if tenant_id:
            query['and'].append({'=': {'project_id': tenant_id}})

        gb = []
        if groupby:
            for elem in groupby.split(','):
                if elem in self.groupby_keys:
                    gb.append(self.groupby_values[
                        self.groupby_keys.index(elem)])
        # Setting gb to None instead of an empty list
        gb = gb if len(gb) > 0 else None

        # build aggregration operation
        op = ['aggregate', 'sum', ['metric', 'price', 'sum']]

        try:
            aggregates = self._conn.aggregates.fetch(
                op,
                start=begin,
                stop=end,
                groupby=gb,
                search=query)
        # No 'price' metric found
        except gexceptions.BadRequest:
            return [dict(begin=begin, end=end, rate=0)]

        # In case no group_by was specified
        if not isinstance(aggregates, list):
            aggregates = [aggregates]
        total_list = list()
        for aggregate in aggregates:
            if groupby:
                measures = aggregate['measures']['measures']['aggregated']
            else:
                measures = aggregate['measures']['aggregated']
            if len(measures) > 0:
                rate = sum(measure[2] for measure in measures
                           if (measure[1] == self._period))
                total = dict(begin=begin, end=end, rate=rate)
                if gb:
                    for value in gb:
                        key = self.groupby_keys[
                            self.groupby_values.index(value)]
                        total[key] = aggregate['group'][value].replace(
                            RESOURCE_TYPE_NAME_ROOT, '')
                total_list.append(total)

        return total_list

    def _append_measurements(self, resource, data, tenant_id):
        if not self._measurements.get(tenant_id, None):
            self._measurements[tenant_id] = {}
        measurements = self._measurements[tenant_id]
        if not measurements.get(resource['id'], None):
            measurements[resource['id']] = {
                key: list() for key in resource['metrics'].values()
            }
        for metric_name, metric_id in resource['metrics'].items():
            measurement = data.get(metric_name, None)
            if measurement is not None:
                measurements[resource['id']][metric_id].append(
                    float(measurement)
                    if isinstance(measurement, decimal.Decimal)
                    else measurement)

    def append_time_frame(self, res_type, frame, tenant_id):
        flat_frame = ck_utils.flat_dict(frame)
        resource = self._find_resource(res_type, flat_frame['id'])
        if not resource:
            resource = self._create_resource(res_type, tenant_id, flat_frame)
        self._append_measurements(resource, flat_frame, tenant_id)

    def get_tenants(self, begin, end):
        query = {'like': {'type': RESOURCE_TYPE_NAME_ROOT + '%'}}
        r = self._conn.metric.aggregation(
            metrics='price',
            query=query,
            start=begin,
            stop=end,
            aggregation='sum',
            granularity=self._period,
            needed_overlap=0,
            groupby='project_id')
        projects = list()
        for measures in r:
            projects.append(measures['group']['project_id'])
        return projects

    @staticmethod
    def _get_time_query(start, end, resource_type, tenant_id=None):
        query = {'and': [{
            'or': [
                {'=': {'ended_at': None}},
                {'<=': {'ended_at': end}}
            ]
        },
            {'>=': {'started_at': start}},
            {'=': {'type': resource_type}},
        ]
        }
        if tenant_id:
            query['and'].append({'=': {'project_id': tenant_id}})
        return query

    def _get_resources(self, resource_type, start, end, tenant_id=None):
        """Returns the resources of the given type in the given period"""
        return self._conn.resource.search(
            resource_type=resource_type,
            query=self._get_time_query(start, end, resource_type, tenant_id),
            details=True)

    def _format_frame(self, res_type, resource, desc, measure, tenant_id):
        res_type_info = self._resource_type_data.get(res_type, None)
        if not res_type_info:
            return dict()

        start = measure[0]
        stop = start + datetime.timedelta(seconds=self._period)

        # Getting price
        price = decimal.Decimal(measure[2])
        price_dict = {'price': float(price)}

        # Getting vol
        if isinstance(res_type_info['qty_metric'], six.text_type):
            try:
                qty = self._conn.metric.get_measures(
                    resource['metrics'][res_type_info['qty_metric']],
                    aggregation='sum',
                    start=start, stop=stop,
                    refresh=True)[-1][2]
            except IndexError:
                qty = 0
        else:
            qty = res_type_info['qty_metric']
        vol_dict = {'qty': decimal.Decimal(qty), 'unit': resource['unit']}

        # Period
        period_dict = {
            'begin': ck_utils.dt2iso(start),
            'end': ck_utils.dt2iso(stop),
        }

        # Formatting
        res_dict = dict()
        res_dict['desc'] = desc
        res_dict['vol'] = vol_dict
        res_dict['rating'] = price_dict
        res_dict['tenant_id'] = tenant_id

        return {
            'usage': {res_type: [res_dict]},
            'period': period_dict,
        }

    def resource_info(self, resource_type, start, end, tenant_id=None):
        """Returns a dataframe for the given resource type"""
        try:
            res_type_info = self._resource_type_data.get(resource_type, None)
            resource_name = res_type_info['name']
        except (KeyError, AttributeError):
            raise UnknownResourceType(resource_type)
        attributes = res_type_info['attributes'] \
            + res_type_info['required_attributes']
        output = list()
        query = self._get_time_query(start, end, resource_name, tenant_id)
        measures = self._conn.metric.aggregation(
            metrics='price',
            resource_type=resource_name,
            query=query,
            start=start,
            stop=end,
            granularity=self._period,
            aggregation='sum',
            needed_overlap=0,
            groupby=['type', 'id'],
        )
        for resource_measures in measures:
            resource_desc = None
            resource = None
            for measure in resource_measures['measures']:
                if not resource_desc:
                    resource = self._get_resource(
                        resource_type, resource_measures['group']['id'])
                    if not resource:
                        continue
                    desc = {attr.replace(METADATA_NAME_ROOT, ''):
                            resource.get(attr, None) for attr in attributes}
                formatted_frame = self._format_frame(
                    resource_type, resource, desc, measure, tenant_id)
                output.append(formatted_frame)
        return output

    def get_time_frame(self, begin, end, **filters):
        tenant_id = filters.get('tenant_id', None)
        resource_types = [filters.get('res_type', None)]
        if not resource_types[0]:
            resource_types = self._resource_type_data.keys()
        output = list()
        for resource_type in resource_types:
            output += self.resource_info(resource_type, begin, end, tenant_id)
        return output
