# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
# @author: Stéphane Albert
#
from oslo_config import cfg
import oslo_messaging as messaging

TRANSPORT = None


def init():
    global TRANSPORT
    if not TRANSPORT:
        TRANSPORT = messaging.get_transport(cfg.CONF)
    return TRANSPORT


def get_client(target, version_cap=None):
    assert TRANSPORT is not None
    return messaging.RPCClient(TRANSPORT,
                               target,
                               version_cap=version_cap)


def get_server(target, endpoints):
    assert TRANSPORT is not None
    return messaging.get_rpc_server(TRANSPORT,
                                    target,
                                    endpoints,
                                    executor='eventlet')
