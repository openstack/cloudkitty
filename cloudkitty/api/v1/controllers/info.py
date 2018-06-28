# -*- coding: utf-8 -*-
# Copyright 2016 Objectif Libre
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
# @author: Maxime Cottret
#
from oslo_config import cfg
from oslo_log import log as logging
import pecan
from pecan import rest
import six
import voluptuous
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import info as info_models
from cloudkitty.api.v1 import types as ck_types
from cloudkitty import collector
from cloudkitty.common import policy
from cloudkitty import utils as ck_utils


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


def get_all_metrics():
    try:
        metrics_conf = collector.validate_conf(
            ck_utils.load_conf(CONF.collect.metrics_conf))
    except (voluptuous.Invalid, voluptuous.MultipleInvalid):
        msg = 'Invalid endpoint: no metrics in current configuration.'
        pecan.abort(405, msg)

    policy.authorize(pecan.request.context, 'info:list_metrics_info', {})
    metrics_info_list = []
    for metric_name, metric in metrics_conf.items():
        info = metric.copy()
        info['metric_id'] = info['alt_name']
        metrics_info_list.append(
            info_models.CloudkittyMetricInfo(**info))
    return info_models.CloudkittyMetricInfoCollection(
        metrics=metrics_info_list)


def _find_metric(name, conf):
    for metric_name, metric in conf.items():
        if metric['alt_name'] == name:
            return metric


def get_one_metric(metric_name):
    try:
        metrics_conf = collector.validate_conf(
            ck_utils.load_conf(CONF.collect.metrics_conf))
    except (voluptuous.Invalid, voluptuous.MultipleInvalid):
        msg = 'Invalid endpoint: no metrics in current configuration.'
        pecan.abort(405, msg)

    policy.authorize(pecan.request.context, 'info:get_metric_info', {})
    metric = _find_metric(metric_name, metrics_conf)
    if not metric:
        pecan.abort(404, six.text_type(metric_name))
    info = metric.copy()
    info['metric_id'] = info['alt_name']
    return info_models.CloudkittyMetricInfo(**info)


class MetricInfoController(rest.RestController):
    """REST Controller managing collected metrics information

    independently of their services.
    If no metrics are defined in conf, return 405 for each endpoint.
    """

    @wsme_pecan.wsexpose(info_models.CloudkittyMetricInfoCollection)
    def get_all(self):
        """Get the metric list.

        :return: List of every metrics.
        """
        return get_all_metrics()

    @wsme_pecan.wsexpose(info_models.CloudkittyMetricInfo, wtypes.text)
    def get_one(self, metric_name):
        """Return a metric.

        :param metric_name: name of the metric.
        """
        return get_one_metric(metric_name)


class ServiceInfoController(rest.RestController):
    """REST Controller managing collected services information."""

    @wsme_pecan.wsexpose(info_models.CloudkittyMetricInfoCollection)
    def get_all(self):
        """Get the service list (deprecated).

        :return: List of every services.
        """
        LOG.warning("Services based endpoints are deprecated. "
                    "Please use metrics based enpoints instead.")
        return get_all_metrics()

    @wsme_pecan.wsexpose(info_models.CloudkittyMetricInfo, wtypes.text)
    def get_one(self, service_name):
        """Return a service (deprecated).

        :param service_name: name of the service.
        """
        LOG.warning("Services based endpoints are deprecated. "
                    "Please use metrics based enpoints instead.")
        return get_one_metric(service_name)


class InfoController(rest.RestController):
    """REST Controller managing Cloudkitty general information."""

    services = ServiceInfoController()
    metrics = MetricInfoController()

    _custom_actions = {'config': ['GET']}

    @wsme_pecan.wsexpose({
        str: ck_types.MultiType(wtypes.text, int, float, dict, list)
    })
    def config(self):
        """Return current configuration."""
        policy.authorize(pecan.request.context, 'info:get_config', {})
        return ck_utils.load_conf(CONF.collect.metrics_conf)
