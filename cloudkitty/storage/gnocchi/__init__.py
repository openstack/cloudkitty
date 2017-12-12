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

import dateutil.parser
from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
import six

from cloudkitty import storage
from cloudkitty import utils as ck_utils

LOG = log.getLogger(__name__)
CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)

GNOCCHI_STORAGE_OPTS = 'storage_gnocchi'
gnocchi_storage_opts = [
    cfg.StrOpt('archive_policy_name',
               default='rating',
               help='Gnocchi storage archive policy name.'),
    # The archive policy definition MUST include the collect period granularity
    cfg.StrOpt('archive_policy_definition',
               default='[{"granularity": '
                       + six.text_type(METRICS_CONF['period']) +
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
            GNOCCHI_STORAGE_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            GNOCCHI_STORAGE_OPTS,
            auth=self.auth)
        self._conn = gclient.Client('1', session=self.session)
        self._measures = {}
        self._archive_policy_name = (
            CONF.storage_gnocchi.archive_policy_name)
        self._archive_policy_definition = json.loads(
            CONF.storage_gnocchi.archive_policy_definition)
        self._period = METRICS_CONF['period']
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
        # Creates state resource if it doesn't exist
        try:
            self._conn.resource_type.create(
                {'name': CLOUDKITTY_STATE_RESOURCE})
        except gexceptions.ResourceAlreadyExists:
            pass

    def _get_or_create_resource(self, resource_type, tenant_id):
        """Return the id of a resource or create it.

        :param resource_type: The type of the resource.
        :type metric_name: str
        :param tenant_id: Owner's resource tenant id.
        :type metric_name: str
        """
        query = {"=": {"project_id": tenant_id}}
        resources = self._conn.resource.search(
            resource_type=resource_type,
            query=query,
            limit=1)
        if not resources:
            # NOTE(sheeprine): We don't have the user id information and we are
            # doing rating on a per tenant basis. Put garbage in it
            resource = self._conn.resource.create(
                resource_type=resource_type,
                resource={'id': uuidutils.generate_uuid(),
                          'user_id': None,
                          'project_id': tenant_id})
            return resource['id']
        return resources[0]['id']

    def _get_or_create_metric(self, metric_name, resource_id):
        """Return the metric id from a metric or create it.

        :param metric_name: The name of the metric.
        :type metric_name: str
        :param resource_id: Resource id containing the metric.
        :type metric_name: str
        """
        resource = self._conn.resource.get(
            resource_type='generic',
            resource_id=resource_id,
            history=False)
        metric_id = resource["metrics"].get(metric_name)
        if not metric_id:
            new_metric = {}
            new_metric["archive_policy_name"] = self._archive_policy_name
            new_metric["name"] = metric_name
            new_metric["resource_id"] = resource_id
            metric = self._conn.metric.create(new_metric)
            metric_id = metric['id']
        return metric_id

    def _pre_commit(self, tenant_id):
        measures = self._measures.pop(tenant_id, {})
        self._measures[tenant_id] = dict()
        for resource_id, metrics in measures.items():
            total = metrics.pop('total.cost')
            total_id = self._get_or_create_metric(
                'total.cost',
                resource_id)
            # TODO(sheeprine): Find a better way to handle total
            total_value = sum([decimal.Decimal(val["value"]) for val in total])
            total_timestamp = max([dateutil.parser.parse(val["timestamp"])
                                   for val in total])
            self._measures[tenant_id][total_id] = [{
                'timestamp': total_timestamp.isoformat(),
                'value': six.text_type(total_value)}]
            for metric_name, values in metrics.items():
                metric_id = self._get_or_create_metric(
                    metric_name,
                    resource_id)
                self._measures[tenant_id][metric_id] = values
        state_resource_id = self._get_or_create_resource(
            CLOUDKITTY_STATE_RESOURCE,
            tenant_id)
        state_metric_id = self._get_or_create_metric(
            CLOUDKITTY_STATE_METRIC,
            state_resource_id)
        self._measures[tenant_id][state_metric_id] = [{
            'timestamp': self.usage_start_dt.get(tenant_id).isoformat(),
            'value': 1}]

    def _commit(self, tenant_id):
        if tenant_id in self._measures:
            self._conn.metric.batch_metrics_measures(
                self._measures[tenant_id])

    def _post_commit(self, tenant_id):
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
        for metric_name, metrics in data.items():
            for item in metrics:
                resource_id = item["desc"]["resource_id"]
                price = item["rating"]["price"]
                self._append_metric(
                    resource_id,
                    metric_name + ".cost",
                    price,
                    tenant_id)
                self._append_metric(
                    resource_id,
                    'total.cost',
                    price,
                    tenant_id)
                self._has_data[tenant_id] = True

    def set_state(self, state, tenant_id):
        state_resource_id = self._get_or_create_resource(
            CLOUDKITTY_STATE_RESOURCE,
            tenant_id)
        state_metric_id = self._get_or_create_metric(
            CLOUDKITTY_STATE_METRIC,
            state_resource_id)
        self._conn.metric.add_measures(
            state_metric_id,
            [{'timestamp': state.isoformat(),
             'value': 1}])

    def get_state(self, tenant_id=None):
        # Return the last written frame's timestamp.
        query = {"=": {"project_id": tenant_id}} if tenant_id else {}
        state_resource_id = self._get_or_create_resource(
            CLOUDKITTY_STATE_RESOURCE,
            tenant_id)
        try:
            # (aolwas) add "refresh=True" to be sure to get all posted
            # measures for this particular metric
            r = self._conn.metric.get_measures(
                metric=CLOUDKITTY_STATE_METRIC,
                resource_id=state_resource_id,
                query=query,
                aggregation="sum",
                limit=1,
                granularity=self._period,
                needed_overlap=0,
                refresh=True)
        except gexceptions.MetricNotFound:
            return
        if len(r) > 0:
            # NOTE(lukapeschke) Since version 5.0.0, gnocchiclient returns a
            # datetime object instead of a timestamp. This fixture is made
            # to ensure compatibility with all versions
            try:
                # (aolwas) According http://gnocchi.xyz/rest.html#metrics,
                # gnocchi always returns measures ordered by timestamp
                return ck_utils.dt2ts(dateutil.parser.parse(r[-1][0]))
            except TypeError:
                return ck_utils.dt2ts(r[-1][0])

    def get_total(self, begin=None, end=None, tenant_id=None,
                  service=None, groupby=None):
        # Get total rate in timeframe from gnocchi
        metric = "total.cost"
        if service:
            metric = service + ".cost"
        # We need to pass a query to force a post in gnocchi client metric
        # aggregation, so we use one that always meets
        query = {"and": [{">": {"started_at": "1900-01-01T00:00"}}]}
        if tenant_id:
            query = {"=": {"project_id": tenant_id}}
        # TODO(Aaron): need support with groupby
        if groupby:
            LOG.warning('Now get total with groupby not support '
                        'in gnocchi storage backend')
        # TODO(sheeprine): Use server side aggregation
        r = self._conn.metric.aggregation(metrics=metric, query=query,
                                          start=begin, stop=end,
                                          aggregation="sum",
                                          granularity=self._period,
                                          needed_overlap=0)

        rate = sum([measure[2] for measure in r]) if len(r) else 0
        # Return a list of dict
        totallist = []
        total = dict(begin=begin, end=end, rate=rate)
        totallist.append(total)
        return totallist

    def get_tenants(self, begin, end):
        # We need to pass a query to force a post in gnocchi client metric
        # aggregation, so we use one that always meets
        query = {'=': {'type': 'cloudkitty_state'}}
        r = self._conn.metric.aggregation(
            metrics=CLOUDKITTY_STATE_METRIC,
            query=query,
            start=begin,
            stop=end,
            aggregation="sum",
            granularity=self._period,
            needed_overlap=0,
            resource_type=CLOUDKITTY_STATE_RESOURCE,
            groupby="project_id")
        projects = [measures["group"]["project_id"]
                    for measures in r if len(measures["measures"])]
        if len(projects) > 0:
            return projects
        return []

    def _get_resource_data(self, res_type, resource_id, begin, end):
        # Get resource information from gnocchi
        return self._collector.resource_info(
            resource_name=res_type,
            start=begin,
            end=end,
            project_id=None)

    def _to_cloudkitty(self, res_type, resource_data, measure):
        # NOTE(lukapeschke) Since version 5.0.0, gnocchiclient returns a
        # datetime object instead of a timestamp. This fixture is made
        # to ensure compatibility with all versions
        try:
            begin = dateutil.parser.parse(measure[0])
            end = (dateutil.parser.parse(measure[0]) +
                   datetime.timedelta(seconds=self._period))
        except TypeError:
            begin = measure[0]
            end = begin + datetime.timedelta(seconds=self._period)
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
        tenant_id = filters.get('tenant_id')
        query = dict()
        if tenant_id:
            query['='] = {'project_id': tenant_id}
        else:
            # NOTE(sheeprine): Dummy filter to comply with gnocchi
            query['!='] = {'project_id': None}
        try:
            res_map = METRICS_CONF['services_objects']
        except KeyError:
            res_map = self._collector.retrieve_mappings
        res_type = filters.get('res_type')
        resources = [res_type] if res_type else res_map.keys()
        ck_res = []
        for resource in resources:
            resource_type = res_map[resource]
            r = self._conn.metric.aggregation(
                metrics=resource + ".cost",
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
                            res_type=resource,
                            resource_id=resource_measures["group"]["id"],
                            begin=begin,
                            end=end)
                    ck_res.append(
                        self._to_cloudkitty(
                            res_type=resource,
                            resource_data=resource_data,
                            measure=measure))
        return ck_res
