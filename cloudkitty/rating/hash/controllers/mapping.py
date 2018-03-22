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
from cloudkitty.rating.hash.datamodels import group as group_models
from cloudkitty.rating.hash.datamodels import mapping as mapping_models
from cloudkitty.rating.hash.db import api as db_api


class HashMapMappingsController(rating.RatingRestControllerBase):
    """Controller responsible of mappings management.

    """

    _custom_actions = {
        'group': ['GET']}

    @wsme_pecan.wsexpose(group_models.Group,
                         ck_types.UuidType())
    def group(self, mapping_id):
        """Get the group attached to the mapping.

        :param mapping_id: UUID of the mapping to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            group_db = hashmap.get_group_from_mapping(
                uuid=mapping_id)
            return group_models.Group(**group_db.export_model())
        except db_api.MappingHasNoGroup as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(mapping_models.MappingCollection,
                         ck_types.UuidType(),
                         ck_types.UuidType(),
                         ck_types.UuidType(),
                         bool,
                         ck_types.UuidType(),
                         bool,
                         status_code=200)
    def get_all(self,
                service_id=None,
                field_id=None,
                group_id=None,
                no_group=False,
                tenant_id=None,
                filter_tenant=False):
        """Get the mapping list

        :param service_id: Service UUID to filter on.
        :param field_id: Field UUID to filter on.
        :param group_id: Group UUID to filter on.
        :param no_group: Filter on orphaned mappings.
        :param tenant_id: Tenant UUID to filter on.
        :param filter_tenant: Explicitly filter on tenant (default is to not
        filter on tenant). Useful if you want to filter on tenant being None.
        :return: List of every mappings.
        """
        hashmap = db_api.get_instance()
        mapping_list = []
        search_opts = dict()
        if filter_tenant:
            search_opts['tenant_uuid'] = tenant_id
        mappings_uuid_list = hashmap.list_mappings(
            service_uuid=service_id,
            field_uuid=field_id,
            group_uuid=group_id,
            no_group=no_group,
            **search_opts)
        for mapping_uuid in mappings_uuid_list:
            mapping_db = hashmap.get_mapping(uuid=mapping_uuid)
            mapping_list.append(mapping_models.Mapping(
                **mapping_db.export_model()))
        res = mapping_models.MappingCollection(mappings=mapping_list)
        return res

    @wsme_pecan.wsexpose(mapping_models.Mapping,
                         ck_types.UuidType())
    def get_one(self, mapping_id):
        """Return a mapping.

        :param mapping_id: UUID of the mapping to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            mapping_db = hashmap.get_mapping(uuid=mapping_id)
            return mapping_models.Mapping(
                **mapping_db.export_model())
        except db_api.NoSuchMapping as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(mapping_models.Mapping,
                         body=mapping_models.Mapping,
                         status_code=201)
    def post(self, mapping_data):
        """Create a mapping.

        :param mapping_data: Informations about the mapping to create.
        """
        hashmap = db_api.get_instance()
        try:
            mapping_db = hashmap.create_mapping(
                value=mapping_data.value,
                map_type=mapping_data.map_type,
                cost=mapping_data.cost,
                field_id=mapping_data.field_id,
                group_id=mapping_data.group_id,
                service_id=mapping_data.service_id,
                tenant_id=mapping_data.tenant_id)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += mapping_db.mapping_id
            return mapping_models.Mapping(
                **mapping_db.export_model())
        except db_api.MappingAlreadyExists as e:
            pecan.abort(409, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         body=mapping_models.Mapping,
                         status_code=302)
    def put(self, mapping_id, mapping):
        """Update a mapping.

        :param mapping_id: UUID of the mapping to update.
        :param mapping: Mapping data to insert.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.update_mapping(
                mapping_id,
                mapping_id=mapping.mapping_id,
                value=mapping.value,
                cost=mapping.cost,
                map_type=mapping.map_type,
                group_id=mapping.group_id,
                tenant_id=mapping.tenant_id)
            pecan.response.headers['Location'] = pecan.request.path
        except db_api.NoSuchMapping as e:
            pecan.abort(404, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         status_code=204)
    def delete(self, mapping_id):
        """Delete a mapping.

        :param mapping_id: UUID of the mapping to delete.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.delete_mapping(uuid=mapping_id)
        except db_api.NoSuchMapping as e:
            pecan.abort(404, six.text_type(e))
