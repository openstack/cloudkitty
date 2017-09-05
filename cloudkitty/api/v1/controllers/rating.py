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
from oslo_concurrency import lockutils
import pecan
from pecan import rest
from stevedore import extension
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import rating as rating_models
from cloudkitty.common import policy
from cloudkitty import utils as ck_utils

PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'


class RatingModulesMixin(object):
    def reload_extensions(self):
        lock = lockutils.lock('rating-modules')
        with lock:
            ck_utils.refresh_stevedore(PROCESSORS_NAMESPACE)
            # FIXME(sheeprine): Implement RPC messages to trigger reload on
            # processors
            self.extensions = extension.ExtensionManager(
                PROCESSORS_NAMESPACE,
                # FIXME(sheeprine): don't want to load it here as we just need
                # the controller
                invoke_on_load=True)
            if not self._first_call:
                self.notify_reload()
            else:
                self._first_call = False

    def notify_reload(self):
        client = pecan.request.rpc_client.prepare(namespace='rating',
                                                  version='1.1')
        client.cast({}, 'reload_modules')

    def __init__(self):
        self._first_call = True
        self.extensions = []
        self.reload_extensions()


class ModulesController(rest.RestController, RatingModulesMixin):
    """REST Controller managing rating modules."""

    def route(self, *args):
        route = args[0]
        if route.startswith('/v1/module_config'):
            policy.authorize(pecan.request.context, 'rating:module_config', {})

        super(ModulesController, self).route(*args)

    @wsme_pecan.wsexpose(rating_models.CloudkittyModuleCollection)
    def get_all(self):
        """return the list of loaded modules.

        :return: name of every loaded modules.
        """
        policy.authorize(pecan.request.context, 'rating:list_modules', {})

        modules_list = []
        lock = lockutils.lock('rating-modules')
        with lock:
            for module in self.extensions:
                infos = module.obj.module_info.copy()
                infos['module_id'] = infos.pop('name')
                modules_list.append(rating_models.CloudkittyModule(**infos))

        return rating_models.CloudkittyModuleCollection(
            modules=modules_list)

    @wsme_pecan.wsexpose(rating_models.CloudkittyModule, wtypes.text)
    def get_one(self, module_id):
        """return a module

        :return: CloudKittyModule
        """
        policy.authorize(pecan.request.context, 'rating:get_module', {})

        try:
            lock = lockutils.lock('rating-modules')
            with lock:
                module = self.extensions[module_id]
        except KeyError:
            pecan.abort(404, 'Module not found.')
        infos = module.obj.module_info.copy()
        infos['module_id'] = infos.pop('name')
        return rating_models.CloudkittyModule(**infos)

    @wsme_pecan.wsexpose(rating_models.CloudkittyModule,
                         wtypes.text,
                         body=rating_models.CloudkittyModule,
                         status_code=302)
    def put(self, module_id, module):
        """Change the state and priority of a module.

        :param module_id: name of the module to modify
        :param module: CloudKittyModule object describing the new desired state
        """
        policy.authorize(pecan.request.context, 'rating:update_module', {})

        try:
            lock = lockutils.lock('rating-modules')
            with lock:
                ext = self.extensions[module_id].obj
        except KeyError:
            pecan.abort(404, 'Module not found.')
        if module.enabled != wtypes.Unset and ext.enabled != module.enabled:
            ext.set_state(module.enabled)
        if module.priority != wtypes.Unset and ext.priority != module.priority:
            ext.set_priority(module.priority)
        pecan.response.location = pecan.request.path


class UnconfigurableController(rest.RestController):
    """This controller raises an error when requested."""

    @wsme_pecan.wsexpose(None)
    def _default(self):
        self.abort()

    def abort(self):
        pecan.abort(409, "Module is not configurable")


class ModulesExposer(rest.RestController, RatingModulesMixin):
    """REST Controller exposing rating modules.

    This is the controller that exposes the modules own configuration
    settings.
    """

    def __init__(self):
        super(ModulesExposer, self).__init__()
        self._loaded_modules = []
        self.expose_modules()

    def expose_modules(self):
        """Load rating modules to expose API controllers."""
        lock = lockutils.lock('rating-modules')
        with lock:
            for ext in self.extensions:
                # FIXME(sheeprine): we should notify two modules with same name
                name = ext.name
                if not ext.obj.config_controller:
                    ext.obj.config_controller = UnconfigurableController
                # Update extension reference
                setattr(self, name, ext.obj.config_controller())
                if name in self._loaded_modules:
                    self._loaded_modules.remove(name)
            # Clear removed modules
            for module in self._loaded_modules:
                delattr(self, module)
            self._loaded_modules = self.extensions.names()


class RatingController(rest.RestController):
    """The RatingController is exposed by the API.

    The RatingControler connects the ModulesExposer, ModulesController
    and a quote action to the API.
    """

    _custom_actions = {
        'quote': ['POST'],
        'reload_modules': ['GET'],
    }

    modules = ModulesController()
    module_config = ModulesExposer()

    @wsme_pecan.wsexpose(float,
                         body=rating_models.CloudkittyResourceCollection)
    def quote(self, res_data):
        """Get an instant quote based on multiple resource descriptions.

        :param res_data: List of resource descriptions.
        :return: Total price for these descriptions.
        """
        policy.authorize(pecan.request.context, 'rating:quote', {})

        client = pecan.request.rpc_client.prepare(namespace='rating')
        res_dict = {}
        for res in res_data.resources:
            if res.service not in res_dict:
                res_dict[res.service] = []
            json_data = res.to_json()
            res_dict[res.service].extend(json_data[res.service])

        res = client.call({}, 'quote', res_data=[{'usage': res_dict}])
        return res

    @wsme_pecan.wsexpose(None)
    def reload_modules(self):
        """Trigger a rating module list reload.

        """
        policy.authorize(pecan.request.context, 'rating:module_config', {})
        self.modules.reload_extensions()
        self.module_config.reload_extensions()
        self.module_config.expose_modules()
