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
from pecan import hooks

from cloudkitty.common import context
from cloudkitty import messaging


class RPCHook(hooks.PecanHook):
    def __init__(self):
        self._rpc_client = messaging.get_client()

    def before(self, state):
        state.request.rpc_client = self._rpc_client


class StorageHook(hooks.PecanHook):
    def __init__(self, storage_backend):
        self._storage_backend = storage_backend

    def before(self, state):
        state.request.storage_backend = self._storage_backend


class ContextHook(hooks.PecanHook):
    def on_route(self, state):
        state.request.context = context.RequestContext.from_environ(
            state.request.environ)
