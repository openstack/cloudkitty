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

import flask
from oslo_concurrency import lockutils
from stevedore import extension
import voluptuous
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy
from cloudkitty import utils as ck_utils
from cloudkitty.utils import validation as vutils


PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'

MODULE_SCHEMA = {
    voluptuous.Required(
        'description',
        default=None,
    ): vutils.get_string_type(),
    voluptuous.Required(
        'module_id',
        default=None,
    ): vutils.get_string_type(),
    voluptuous.Required(
        'enabled',
        default=None,
    ): voluptuous.Boolean(),
    voluptuous.Required(
        'hot_config',
        default=None,
    ): voluptuous.Boolean(),
    voluptuous.Required(
        'priority',
        default=None,
    ): voluptuous.All(int, min=1),
}


class BaseRatingModule(base.BaseResource):

    @classmethod
    def reload(cls):
        super(BaseRatingModule, cls).reload()
        with lockutils.lock('rating-modules'):
            ck_utils.refresh_stevedore(PROCESSORS_NAMESPACE)
            cls.rating_modules = extension.ExtensionManager(
                PROCESSORS_NAMESPACE, invoke_on_load=True)


class RatingModule(BaseRatingModule):

    @api_utils.add_output_schema(MODULE_SCHEMA)
    def get(self, module_id):
        policy.authorize(flask.request.context, 'v2_rating:get_module', {})
        try:
            module = self.rating_modules[module_id]
        except KeyError:
            raise http_exceptions.NotFound(
                "Module '{}' not found".format(module_id))
        infos = module.obj.module_info.copy()
        return {
            'module_id': module_id,
            'description': infos['description'],
            'enabled': infos['enabled'],
            'hot_config': infos['hot_config'],
            'priority': infos['priority'],
        }


class RatingModuleList(BaseRatingModule):

    @api_utils.add_output_schema({
        'modules': [MODULE_SCHEMA],
    })
    def get(self):
        modules = []
        for module in self.rating_modules:
            infos = module.obj.module_info.copy()
            modules.append({
                'module_id': infos['name'],
                'description': infos['description'],
                'enabled': infos['enabled'],
                'hot_config': infos['hot_config'],
                'priority': infos['priority'],
            })
        return {'modules': modules}
