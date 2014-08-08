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
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.controllers import v1
from cloudkitty.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class APILink(wtypes.Base):

    type = wtypes.text

    rel = wtypes.text

    href = wtypes.text


class APIMediaType(wtypes.Base):

    base = wtypes.text

    type = wtypes.text


class APIVersion(wtypes.Base):

    id = wtypes.text

    status = wtypes.text

    links = [APILink]

    media_types = [APIMediaType]


class RootController(rest.RestController):

    v1 = v1.V1Controller()

    @wsme_pecan.wsexpose([APIVersion])
    def get(self):
        # TODO(sheeprine): Maybe we should store all the API version
        # informations in every API modules
        ver1 = APIVersion(
            id='v1',
            status='EXPERIMENTAL',
            updated='2014-06-02T00:00:00Z',
            links=[
                APILink(
                    rel='self',
                    href='{scheme}://{host}/v1'.format(
                        scheme=pecan.request.scheme,
                        host=pecan.request.host
                    )
                )
            ],
            media_types=[]
        )

        versions = []
        versions.append(ver1)

        return versions
