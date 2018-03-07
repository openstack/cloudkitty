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
import decimal

from keystoneauth1 import loading as ks_loading
from keystoneclient.v3 import client as ks_client
from monascaclient import client as mclient
from oslo_config import cfg
from oslo_log import log as logging

from cloudkitty import collector
from cloudkitty import transformer
from cloudkitty import utils as ck_utils


LOG = logging.getLogger(__name__)

MONASCA_API_VERSION = '2_0'
COLLECTOR_MONASCA_OPTS = 'collector_monasca'
collector_monasca_opts = ks_loading.get_auth_common_conf_options()

cfg.CONF.register_opts(collector_monasca_opts, COLLECTOR_MONASCA_OPTS)
ks_loading.register_session_conf_options(
    cfg.CONF,
    COLLECTOR_MONASCA_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    COLLECTOR_MONASCA_OPTS)
CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)


class EndpointNotFound(Exception):
    """Exception raised if the Monasca endpoint is not found"""
    pass


class MonascaCollector(collector.BaseCollector):
    collector_name = 'monasca'
    dependencies = ['CloudKittyFormatTransformer']
    retrieve_mappings = {
        'compute': 'cpu',
        'image': 'image.size',
        'volume': 'volume.size',
        'network.floating': 'ip.floating',
        'network.bw.in': 'network.incoming.bytes',
        'network.bw.out': 'network.outgoing.bytes',
    }
    metrics_mappings = {
        'compute': [
            {'cpu': 'max'},
            {'vpcus': 'max'},
            {'memory': 'max'}],
        'image': [
            {'image.size': 'max'},
            {'image.download': 'max'},
            {'image.serve': 'max'}],
        'volume': [
            {'volume.size': 'max'}],
        'network.bw.in': [
            {'network.incoming.bytes': 'max'}],
        'network.bw.out': [
            {'network.outgoing.bytes': 'max'}],
        'network.floating': [
            {'ip.floating': 'max'}],
    }
    # (qty, unit). qty must be either a metric name, an integer
    # or a decimal.Decimal object
    units_mappings = {
        'compute': (1, 'instance'),
        'image': ('image.size', 'MiB'),
        'volume': ('volume.size', 'GiB'),
        'network.bw.out': ('network.outgoing.bytes', 'MB'),
        'network.bw.in': ('network.incoming.bytes', 'MB'),
        'network.floating': (1, 'ip'),
    }
    default_unit = (1, 'unknown')

    def __init__(self, transformers, **kwargs):
        super(MonascaCollector, self).__init__(transformers, **kwargs)

        self.t_cloudkitty = self.transformers['CloudKittyFormatTransformer']

        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            COLLECTOR_MONASCA_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            COLLECTOR_MONASCA_OPTS,
            auth=self.auth)
        self.ks_client = ks_client.Client(session=self.session)
        self.mon_endpoint = self._get_monasca_endpoint()
        if not self.mon_endpoint:
            raise EndpointNotFound()
        # NOTE (lukapeschke) session authentication should be possible starting
        # with OpenStack Q release.
        self._conn = mclient.Client(
            api_version=MONASCA_API_VERSION,
            session=self.session,
            endpoint=self.mon_endpoint)

    # NOTE(lukapeschke) This function should be removed as soon as the endpoint
    # it no longer required by monascaclient
    def _get_monasca_endpoint(self, service_name='monasca',
                              endpoint_interface_type='public'):
        service_list = self.ks_client.services.list(name=service_name)
        if not service_list:
            return None
        mon_service = service_list[0]
        endpoints = self.ks_client.endpoints.list(mon_service.id)
        for endpoint in endpoints:
            if endpoint.interface == endpoint_interface_type:
                return endpoint.url
        return None

    def _get_metadata(self, resource_type, transformers, conf):
        info = {}
        info['unit'] = conf['metrics'][resource_type]['unit']

        start = ck_utils.dt2ts(ck_utils.get_month_start())
        end = ck_utils.dt2ts(ck_utils.get_month_end())

        try:
            resource = self.active_resources(
                resource_type,
                start,
                end,
                None,
            )[0]
        except IndexError:
            resource = {}
        info['metadata'] = resource.get('dimensions', {}).keys()

        service_metrics = METRICS_CONF['services_metrics'][resource_type]
        for service_metric in service_metrics:
            metric, statistics = list(service_metric.items())[0]
            info['metadata'].append(metric)
        return info

    # NOTE(lukapeschke) if anyone sees a better way to do this,
    # please make a patch
    @classmethod
    def get_metadata(cls, resource_type, transformers, conf):
        args = {
            'transformers': transformer.get_transformers(),
            'period': conf['period']}
        tmp = cls(**args)
        return tmp._get_metadata(resource_type, transformers, conf)

    def _get_resource_metadata(self, resource_type, start,
                               end, resource_id, conf):
        meter = conf['metrics'][resource_type]['resource']

        if not meter:
            return {}
        measurements = self._conn.metrics.list_measurements(
            name=meter,
            start_time=ck_utils.ts2dt(start),
            end_time=ck_utils.ts2dt(end),
            merge_metrics=True,
            dimensions={'resource_id': resource_id},
        )
        try:
            # Getting the last measurement of given period
            metadata = measurements[-1]['measurements'][-1][2]
        except (KeyError, IndexError):
            metadata = {}
        return metadata

    def _get_resource_qty(self, meter, start, end, resource_id, statistics):
        # NOTE(lukapeschke) the period trick is used to aggregate
        # the measurements
        period = end - start
        statistics = self._conn.metrics.list_statistics(
            name=meter,
            start_time=ck_utils.ts2dt(start),
            end_time=ck_utils.ts2dt(end),
            dimensions={'resource_id': resource_id},
            statistics=statistics,
            period=period,
            merge_metrics=True,
        )
        try:
            # If several statistics are returned (should not happen),
            # use the latest
            qty = decimal.Decimal(statistics[-1]['statistics'][-1][1])
        except (KeyError, IndexError):
            qty = decimal.Decimal(0)
        return qty

    def _is_resource_active(self, meter, resource_id, start, end):
        measurements = self._conn.metrics.list_measurements(
            name=meter,
            start_time=ck_utils.ts2dt(start),
            end_time=ck_utils.ts2dt(end),
            group_by='resource_id',
            merge_metrics=True,
            dimensions={'resource_id': resource_id},
        )
        return len(measurements) > 0

    def active_resources(self, resource_type, start,
                         end, project_id, conf, **kwargs):
        meter = conf['metrics'][resource_type]['resource']

        if not meter:
            return {}
        dimensions = {}
        if project_id:
            dimensions['project_id'] = project_id
        dimensions.update(kwargs)
        resources = self._conn.metrics.list(name=meter, dimensions=dimensions)
        output = []
        for resource in resources:
            try:
                resource_id = resource['dimensions']['resource_id']
                if (resource_id not in
                    [item['dimensions']['resource_id'] for item in output]
                        and self._is_resource_active(meter, resource_id,
                                                     start, end)):
                    output.append(resource)
            except KeyError:
                continue
        return output

    def _expand_metrics(self, resource, resource_id,
                        mappings, start, end, resource_type):
        for mapping in mappings:
            name, statistics = list(mapping.items())[0]
            qty = self._get_resource_qty(
                name,
                start,
                end,
                resource_id,
                statistics,
            )

            conv_data = METRICS_CONF['metrics'][resource_type].get(name)
            if conv_data:
                resource[name] = ck_utils.convert_unit(
                    qty,
                    conv_data.get('factor', 1),
                    conv_data.get('offset', 0),
                )

    def resource_info(self, resource_type, start, end,
                      project_id, q_filter=None):
        met = self.conf['metrics'][resource_type]
        unit = met['unit']
        qty = 1 if met.get('countable_unit') else met['resource']

        active_resources = self.active_resources(
            resource_type, start, end, project_id
        )

        resource_data = []
        for resource in active_resources:
            resource_id = resource['dimensions']['resource_id']
            data = resource['dimensions']
            mappings = (
                resource_type,
                METRICS_CONF['metrics'][resource_type]['aggregation_method'],
            )

            self._expand_metrics(
                data,
                resource_id,
                mappings,
                start,
                end,
                resource_type,
            )
            resource_qty = qty
            if not (isinstance(qty, int) or isinstance(qty, decimal.Decimal)):
                resource_qty = METRICS_CONF['services_objects'][resource_type]
                resource_qty = data[resource_qty]

            resource = self.t_cloudkitty.format_item(data, unit, resource_qty)
            resource['desc']['resource_id'] = resource_id
            resource['resource_id'] = resource_id
            resource_data.append(resource)
        return resource_data

    def retrieve(self, resource_type, start, end, project_id, q_filter=None):
        resources = self.resource_info(resource_type, start, end,
                                       project_id=project_id,
                                       q_filter=q_filter)
        if not resources:
            raise collector.NoDataCollected(self.collector_name, resource_type)
        return self.t_cloudkitty.format_service(resource_type, resources)
