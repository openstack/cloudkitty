# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty import rating
from cloudkitty.rating.hash.controllers import field as field_api
from cloudkitty.rating.hash.controllers import group as group_api
from cloudkitty.rating.hash.controllers import mapping as mapping_api
from cloudkitty.rating.hash.controllers import service as service_api
from cloudkitty.rating.hash.controllers import threshold as threshold_api
from cloudkitty.rating.hash.datamodels import mapping as mapping_models


class HashMapConfigController(rating.RatingRestControllerBase):
    """Controller exposing all management sub controllers.

    """

    _custom_actions = {
        'types': ['GET']
    }

    services = service_api.HashMapServicesController()
    fields = field_api.HashMapFieldsController()
    groups = group_api.HashMapGroupsController()
    mappings = mapping_api.HashMapMappingsController()
    thresholds = threshold_api.HashMapThresholdsController()

    @wsme_pecan.wsexpose([wtypes.text])
    def get_types(self):
        """Return the list of every mapping type available.

        """
        return mapping_models.MAP_TYPE.values
