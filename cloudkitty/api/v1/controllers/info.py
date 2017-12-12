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
import pecan
from pecan import rest
import six
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import info as info_models
from cloudkitty.api.v1 import types as ck_types
from cloudkitty import collector
from cloudkitty.common import policy
from cloudkitty import utils as ck_utils

CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)

METADATA = collector.get_collector_metadata()


class ServiceInfoController(rest.RestController):
    """REST Controller mananging collected services information."""

    @wsme_pecan.wsexpose(info_models.CloudkittyServiceInfoCollection)
    def get_all(self):
        """Get the service list.

        :return: List of every services.
        """
        policy.authorize(pecan.request.context, 'info:list_services_info', {})
        services_info_list = []
        for service, metadata in METADATA.items():
            info = metadata.copy()
            info['service_id'] = service
            services_info_list.append(
                info_models.CloudkittyServiceInfo(**info))
        return info_models.CloudkittyServiceInfoCollection(
            services=services_info_list)

    @wsme_pecan.wsexpose(info_models.CloudkittyServiceInfo, wtypes.text)
    def get_one(self, service_name):
        """Return a service.

        :param service_name: name of the service.
        """
        policy.authorize(pecan.request.context, 'info:get_service_info', {})
        try:
            info = METADATA[service_name].copy()
            info['service_id'] = service_name
            return info_models.CloudkittyServiceInfo(**info)
        except KeyError:
            pecan.abort(404, six.text_type(service_name))


class InfoController(rest.RestController):
    """REST Controller managing Cloudkitty general information."""

    services = ServiceInfoController()

    _custom_actions = {'config': ['GET']}

    @wsme_pecan.wsexpose({
        str: ck_types.MultiType(wtypes.text, int, float, dict, list)
    })
    def config(self):
        """Return current configuration."""
        policy.authorize(pecan.request.context, 'info:get_config', {})
        info = {}
        info["collect"] = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)
        return info
