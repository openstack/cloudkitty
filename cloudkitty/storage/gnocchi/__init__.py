# -*- coding: utf-8 -*-
# Copyright 2016 (c) Openstack Foundation
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
# @author: Sergio Colinas
#
import datetime
import decimal
import json
import uuid

import dateutil.parser
from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log
import six

from cloudkitty import storage
from cloudkitty import utils as ck_utils

LOG = log.getLogger(__name__)
CONF = cfg.CONF

CONF.import_opt('period', 'cloudkitty.collector', 'collect')

STORAGE_GNOCCHI_OPTS = 'storage_gnocchi'
STORAGE_OPTS = [
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
CONF.register_opts(STORAGE_OPTS, STORAGE_GNOCCHI_OPTS)

ks_loading.register_session_conf_options(
    CONF,
    STORAGE_GNOCCHI_OPTS)
ks_loading.register_auth_conf_options(
    CONF,
    STORAGE_GNOCCHI_OPTS)

CLOUDKITTY_STATE_RESOURCE = 'cloudkitty_state'
CLOUDKITTY_STATE_METRIC = 'state'


class GnocchiStorage(storage.BaseStorage):
    """Gnocchi Storage Backend.

    Driver used to add full native support for gnocchi, improving performance
    and taking advantage of gnocchi capabilities.
    """

    def __init__(self, **kwargs):
        super(GnocchiStorage, self).__init__(**kwargs)
        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            STORAGE_GNOCCHI_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            STORAGE_GNOCCHI_OPTS,
            auth=self.auth)
        self._conn = gclient.Client('1', session=self.session)
        self._measures = {}
        self._archive_policy_name = (
            CONF.storage_gnocchi.archive_policy_name)
        self._archive_policy_definition = json.loads(
            CONF.storage_gnocchi.archive_policy_definition)
        self._period = CONF.collect.period
        if "period" in kwargs:
            self._period = kwargs["period"]

    def init(self):
        # Creates rating archive-policy if not exists
        try:
            self._conn.archive_policy.get(self._archive_policy_name)
        except gexceptions.ArchivePolicyNotFound:
            ck_policy = {}
            ck_policy["name"] = self._archive_policy_name
            ck_policy["back_window"] = 0
            ck_policy["aggregation_methods"] = ["sum", ]
            ck_policy["definition"] = self._archive_policy_definition
            self._conn.archive_policy.create(ck_policy)
        # Creates state resource if not exists
        # TODO(sheeprine): Check if it exists before creating
        self._conn.resource_type.create({'name': CLOUDKITTY_STATE_RESOURCE})

    def _get_or_create_metric(self, metric_name, resource_id):
        resource = self._conn.resource.get('generic', resource_id, False)
        metric_id = resource["metrics"].get(metric_name)
        if not metric_id:
            new_metric = {}
            new_metric["archive_policy_name"] = self._archive_policy_name
            new_metric["name"] = metric_name
            new_metric["resource_id"] = resource_id
            metric = self._conn.metric.create(new_metric)
            metric_id = metric["id"]
        return metric_id

    def _pre_commit(self, tenant_id):
        measures = self._measures.pop(tenant_id, {})
        self._measures[tenant_id] = dict()
        for resource_id, metrics in six.iteritems(measures):
            total = metrics.pop('total.cost')
            total_id = self._get_or_create_metric(
                'total.cost',
                resource_id)
            # TODO(sheeprine): Find a better way to handle total
            aux = sum([decimal.Decimal(val["value"]) for val in total])
            total["value"] = six.text_type(aux)
            self._measures[tenant_id][total_id] = [total]
            for metric_name, values in six.iteritems(metrics):
                metric_id = self._get_or_create_metric(
                    metric_name,
                    resource_id)
                self._measures[tenant_id][metric_id] = values

    def _commit(self, tenant_id):
        if tenant_id in self._measures:
            self._conn.metric.batch_metrics_measures(
                self._measures[tenant_id])

    def _post_commit(self, tenant_id):
        # TODO(sheeprine): Better state handling
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}},
                         {"=": {"project_id": tenant_id}}]}
        state_resource = self._conn.resource.search(
            resource_type=CLOUDKITTY_STATE_RESOURCE,
            query=query)
        if not state_resource:
            state_resource = self._conn.resource.create(
                resource_type=CLOUDKITTY_STATE_RESOURCE,
                resource={'id': uuid.uuid4(),
                          'user_id': uuid.uuid4(),
                          'project_id': tenant_id})
        # TODO(sheeprine): Catch good exception
        try:
            state_metric = self._conn.metric.get(
                metric=CLOUDKITTY_STATE_METRIC,
                resource_id=state_resource['id'])
        except Exception:
            state_metric = None
        if not state_metric:
            state_metric = self._conn.metric.create(
                {'name': CLOUDKITTY_STATE_METRIC,
                 'archive_policy_name': self._archive_policy_name,
                 'resource_id': state_resource[0]['id']})
        self._conn.metric.add_measures(
            state_metric['id'],
            {'timestamp': self.usage_start_dt.get(tenant_id).isoformat(),
             'value': 1})
        super(GnocchiStorage, self)._post_commit(tenant_id)
        if tenant_id in self._measures:
            del self._measures[tenant_id]

    def _append_metric(self, resource_id, metric_name, value, tenant_id):
        sample = {}
        sample["timestamp"] = self.usage_start_dt.get(tenant_id).isoformat()
        sample["value"] = six.text_type(value)
        measures = self._measures.get(tenant_id) or dict()
        if not measures:
            self._measures[tenant_id] = measures
        metrics = measures.get(resource_id) or dict()
        if not metrics:
            measures[resource_id] = metrics
        metrics[metric_name] = [sample]

    def _dispatch(self, data, tenant_id):
        for metric_name, metrics in six.iteritems(data):
            for item in metrics:
                resource_id = item["desc"]["resource_id"]
                price = item["rating"]["price"]
                self._append_metric(
                    resource_id,
                    metric_name,
                    price,
                    tenant_id)
                self._append_metric(
                    resource_id,
                    'total.cost',
                    price,
                    tenant_id)
                self._has_data[tenant_id] = True

    def get_state(self, tenant_id=None):
        # Return the last written frame's timestamp.
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}}]}
        if tenant_id:
            query["and"].append(
                {"=": {"project_id": tenant_id}})
        # TODO(sheeprine): Get only latest timestamp
        r = self._conn.metric.aggregation(
            metrics=CLOUDKITTY_STATE_METRIC,
            resource_type=CLOUDKITTY_STATE_RESOURCE,
            query=query,
            aggregation="sum",
            granularity=self._period,
            needed_overlap=0)
        if len(r) > 0:
            return ck_utils.dt2ts(
                max([dateutil.parser.parse(measure[0]) for measure in r]))

    def get_total(self, begin=None, end=None, tenant_id=None, service=None):
        # Get total rate in timeframe from gnocchi
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()
        metric = "total.cost"
        if service:
            metric = service + ".cost"
        # We need to pass a query to force a post in gnocchi client metric
        # aggregation, so we use one that always meets
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}}]}
        if tenant_id:
            query = {"=": {"project_id": tenant_id}}
        # TODO(sheeprine): Use server side aggregation
        r = self._conn.metric.aggregation(metrics=metric, query=query,
                                          start=begin, stop=end,
                                          aggregation="sum",
                                          granularity=self._period,
                                          needed_overlap=0)
        if len(r) > 0:
            return sum([measure[2] for measure in r])
        return 0

    def get_tenants(self, begin=None, end=None):
        # Get rated tenants in timeframe from gnocchi
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()
        # We need to pass a query to force a post in gnocchi client metric
        # aggregation, so we use one that always meets
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}}]}
        r = []
        for metric in self._collector.retrieve_mappings.keys():
            r = self._conn.metric.aggregation(metrics=metric + ".cost",
                                              query=query, start=begin,
                                              stop=end, aggregation="sum",
                                              needed_overlap=0,
                                              groupby="project_id")
            projects = [measures["group"]["project_id"] for measures
                        in r if len(measures["measures"])]
            if len(projects) > 0:
                return projects
        return []

    def _get_resource_data(self, res_type, resource_id, begin, end):
        # Get resource information from gnocchi
        return self._collector.resource_info(
            resource_name=res_type,
            start=begin,
            end=end,
            resource_id=resource_id,
            project_id=None)

    def _to_cloudkitty(self, res_type, resource_data, measure):
        begin = dateutil.parser.parse(measure[0])
        end = (dateutil.parser.parse(measure[0]) +
               datetime.timedelta(seconds=self._period))
        cost = decimal.Decimal(measure[2])
        # Rating informations
        rating_dict = {}
        rating_dict['price'] = cost

        # Encapsulate informations in a resource dict
        res_dict = {}
        # TODO(sheeprine): Properly recurse on elements
        resource_data = resource_data[0]
        res_dict['desc'] = resource_data['desc']
        if "qty" in resource_data["vol"]:
            resource_data["vol"]["qty"] = (
                decimal.Decimal(resource_data["vol"]["qty"]))
        res_dict['vol'] = resource_data['vol']
        res_dict['rating'] = rating_dict
        res_dict['tenant_id'] = resource_data['desc']['project_id']

        # Add resource to the usage dict
        usage_dict = {}
        usage_dict[res_type] = [res_dict]

        # Time informations
        period_dict = {}
        period_dict['begin'] = begin.isoformat()
        period_dict['end'] = end.isoformat()

        # Add period to the resource informations
        ck_dict = {}
        ck_dict['period'] = period_dict
        ck_dict['usage'] = usage_dict
        return ck_dict

    def get_time_frame(self, begin, end, **filters):
        # Request a time frame from the storage backend.
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}}]}
        if 'tenant_id' in filters:
            query["and"].append(
                {"=": {"project_id": filters.get('tenant_id')}})
        res_map = self._collector.retrieve_mappings
        res_type = filters.get('res_type')
        resources = [res_type] if res_type else res_map.keys()
        ck_res = []
        for resource in resources:
            resource_type = res_map[resource]
            r = self._conn.metric.aggregation(
                metrics=[resource + '.cost'],
                resource_type=resource_type,
                query=query,
                start=begin,
                stop=end,
                granularity=self._period,
                aggregation="sum",
                needed_overlap=0,
                groupby=["type", "id"])
            for resource_measures in r:
                resource_data = None
                for measure in resource_measures["measures"]:
                    if not resource_data:
                        resource_data = self._get_resource_data(
                            res_type=resource_type,
                            resource_id=resource_measures["group"]["id"],
                            begin=begin,
                            end=end)
                    ck_res.append(
                        self._to_cloudkitty(
                            res_type=filters.get('res_type'),
                            resource_data=resource_data,
                            measure=measure))
        return ck_res