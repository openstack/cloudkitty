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
import pecan
import six
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1 import types as ck_types
from cloudkitty import rating
from cloudkitty.rating.hash.controllers import field as field_api
from cloudkitty.rating.hash.controllers import mapping as mapping_api
from cloudkitty.rating.hash.datamodels import service as service_models
from cloudkitty.rating.hash.db import api as db_api


class HashMapServicesController(rating.RatingRestControllerBase):
    """Controller responsible of services management.

    """

    fields = field_api.HashMapFieldsController()
    mappings = mapping_api.HashMapMappingsController()

    @wsme_pecan.wsexpose(service_models.ServiceCollection)
    def get_all(self):
        """Get the service list

        :return: List of every services.
        """
        hashmap = db_api.get_instance()
        service_list = []
        services_uuid_list = hashmap.list_services()
        for service_uuid in services_uuid_list:
            service_db = hashmap.get_service(uuid=service_uuid)
            service_list.append(service_models.Service(
                **service_db.export_model()))
        res = service_models.ServiceCollection(services=service_list)
        return res

    @wsme_pecan.wsexpose(service_models.Service, ck_types.UuidType())
    def get_one(self, service_id):
        """Return a service.

        :param service_id: UUID of the service to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            service_db = hashmap.get_service(uuid=service_id)
            return service_models.Service(**service_db.export_model())
        except db_api.NoSuchService as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(service_models.Service,
                         body=service_models.Service,
                         status_code=201)
    def post(self, service_data):
        """Create hashmap service.

        :param service_data: Informations about the service to create.
        """
        hashmap = db_api.get_instance()
        try:
            service_db = hashmap.create_service(service_data.name)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += service_db.service_id
            return service_models.Service(
                **service_db.export_model())
        except db_api.ServiceAlreadyExists as e:
            pecan.abort(409, six.text_type(e))

    @wsme_pecan.wsexpose(None, ck_types.UuidType(), status_code=204)
    def delete(self, service_id):
        """Delete the service and all the sub keys recursively.

        :param service_id: UUID of the service to delete.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.delete_service(uuid=service_id)
        except db_api.NoSuchService as e:
            pecan.abort(404, six.text_type(e))
