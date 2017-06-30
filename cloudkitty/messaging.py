# -*- coding: utf-8 -*-
# Copyright 2016 99Cloud zhangguoqing <zhang.guoqing@99cloud.net>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
import oslo_messaging
from oslo_messaging.rpc import dispatcher

DEFAULT_URL = "__default__"
RPC_TARGET = None
TRANSPORTS = {}


def setup():
    oslo_messaging.set_transport_defaults('cloudkitty')


def get_transport(url=None, optional=False, cache=True):
    """Initialise the oslo_messaging layer."""
    global TRANSPORTS, DEFAULT_URL
    cache_key = url or DEFAULT_URL
    transport = TRANSPORTS.get(cache_key)
    if not transport or not cache:
        try:
            transport = oslo_messaging.get_rpc_transport(cfg.CONF, url)
        except (oslo_messaging.InvalidTransportURL,
                oslo_messaging.DriverLoadFailure):
            if not optional or url:
                # NOTE(sileht): oslo_messaging is configured but unloadable
                # so reraise the exception
                raise
            return None
        else:
            if cache:
                TRANSPORTS[cache_key] = transport
    return transport


def get_target():
    global RPC_TARGET
    if RPC_TARGET is None:
        RPC_TARGET = oslo_messaging.Target(topic='cloudkitty', version='1.0')
    return RPC_TARGET


def get_client(version_cap=None):
    transport = get_transport()
    target = get_target()
    return oslo_messaging.RPCClient(transport, target, version_cap=version_cap)


def get_server(target=None, endpoints=None):
    access_policy = dispatcher.DefaultRPCAccessPolicy
    transport = get_transport()
    if not target:
        target = get_target()
    return oslo_messaging.get_rpc_server(transport, target,
                                         endpoints, executor='eventlet',
                                         access_policy=access_policy)


def cleanup():
    """Cleanup the oslo_messaging layer."""
    global TRANSPORTS, NOTIFIERS
    NOTIFIERS = {}
    for url in TRANSPORTS:
        TRANSPORTS[url].cleanup()
        del TRANSPORTS[url]
