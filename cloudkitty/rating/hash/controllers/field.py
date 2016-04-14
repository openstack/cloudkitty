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
from cloudkitty.rating.hash.datamodels import field as field_models
from cloudkitty.rating.hash.db import api as db_api


class HashMapFieldsController(rating.RatingRestControllerBase):
    """Controller responsible of fields management.

    """

    @wsme_pecan.wsexpose(field_models.FieldCollection,
                         ck_types.UuidType(),
                         status_code=200)
    def get_all(self, service_id):
        """Get the field list.

        :param service_id: Service's UUID to filter on.
        :return: List of every fields.
        """
        hashmap = db_api.get_instance()
        field_list = []
        fields_uuid_list = hashmap.list_fields(service_id)
        for field_uuid in fields_uuid_list:
            field_db = hashmap.get_field(field_uuid)
            field_list.append(field_models.Field(
                **field_db.export_model()))
        res = field_models.FieldCollection(fields=field_list)
        return res

    @wsme_pecan.wsexpose(field_models.Field,
                         ck_types.UuidType(),
                         status_code=200)
    def get_one(self, field_id):
        """Return a field.

        :param field_id: UUID of the field to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            field_db = hashmap.get_field(uuid=field_id)
            return field_models.Field(**field_db.export_model())
        except db_api.NoSuchField as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(field_models.Field,
                         body=field_models.Field,
                         status_code=201)
    def post(self, field_data):
        """Create a field.

        :param field_data: Informations about the field to create.
        """
        hashmap = db_api.get_instance()
        try:
            field_db = hashmap.create_field(
                field_data.service_id,
                field_data.name)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += field_db.field_id
            return field_models.Field(
                **field_db.export_model())
        except db_api.FieldAlreadyExists as e:
            pecan.abort(409, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         status_code=204)
    def delete(self, field_id):
        """Delete the field and all the sub keys recursively.

        :param field_id: UUID of the field to delete.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.delete_field(uuid=field_id)
        except db_api.NoSuchField as e:
            pecan.abort(404, six.text_type(e))
