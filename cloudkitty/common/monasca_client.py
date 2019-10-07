# -*- coding: utf-8 -*-
# Copyright 2019 Objectif Libre
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

from keystoneauth1 import loading as ks_loading
from keystoneclient.v3 import client as ks_client
from monascaclient import client as mclient


MONASCA_API_VERSION = '2_0'


class EndpointNotFound(Exception):
    """Exception raised if the Monasca endpoint is not found"""


# NOTE(lukapeschke) This function should be removed as soon as the endpoint
# it no longer required by monascaclient
def get_monasca_endpoint(cfg, keystone_client):
    service_name = cfg.monasca_service_name
    endpoint_interface_type = cfg.interface

    service_list = keystone_client.services.list(name=service_name)
    if not service_list:
        return None
    mon_service = service_list[0]
    endpoints = keystone_client.endpoints.list(mon_service.id)
    for endpoint in endpoints:
        if endpoint.interface == endpoint_interface_type:
            return endpoint.url
    return None


def get_monasca_client(conf, conf_opts):
    ks_auth = ks_loading.load_auth_from_conf_options(conf, conf_opts)
    session = ks_loading.load_session_from_conf_options(
        conf,
        conf_opts,
        auth=ks_auth)
    keystone_client = ks_client.Client(
        session=session,
        interface=conf[conf_opts].interface)
    mon_endpoint = get_monasca_endpoint(conf[conf_opts], keystone_client)
    if not mon_endpoint:
        raise EndpointNotFound()
    return mclient.Client(
        api_version=MONASCA_API_VERSION,
        session=session,
        endpoint=mon_endpoint)
