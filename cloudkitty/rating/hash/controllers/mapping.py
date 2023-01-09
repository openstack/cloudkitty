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
import datetime
import pecan
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1 import types as ck_types
from cloudkitty.common.custom_session import get_request_user
from cloudkitty import rating
from cloudkitty.rating.common.validations import fields as field_validations
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
            pecan.abort(404, e.args[0])

    @wsme_pecan.wsexpose(mapping_models.MappingCollection,
                         ck_types.UuidType(),
                         ck_types.UuidType(),
                         ck_types.UuidType(),
                         bool,
                         ck_types.UuidType(),
                         bool,
                         bool,
                         datetime.datetime,
                         datetime.datetime,
                         str,
                         str,
                         str,
                         str,
                         bool,
                         bool,
                         status_code=200)
    def get_all(self,
                service_id=None,
                field_id=None,
                group_id=None,
                no_group=False,
                tenant_id=None,
                filter_tenant=False,
                deleted=False,
                start=None,
                end=None,
                updated_by=None,
                created_by=None,
                deleted_by=None,
                description=None,
                is_active=None,
                all=True):
        """Get the mapping list

        :param service_id: Service UUID to filter on.
        :param field_id: Field UUID to filter on.
        :param group_id: Group UUID to filter on.
        :param no_group: Filter on orphaned mappings.
        :param tenant_id: Tenant UUID to filter on.
        :param filter_tenant: Explicitly filter on tenant (default is to not
                              filter on tenant). Useful if you want to filter
                              on tenant being None.
        :param deleted: Show deleted mappings.
        :param start: Mappings with start after date.
        :param end: Mappings with end before date.
        :param updated_by: user uuid to filter on.
        :param created_by: user uuid to filter on.
        :param deleted_by: user uuid to filter on.
        :param description: mapping that contains the text in description.
        :param is_active: only active mappings.
        :param: all: list all rules.
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
            deleted=deleted,
            start=start,
            end=end,
            updated_by=updated_by,
            created_by=created_by,
            deleted_by=deleted_by,
            description=description,
            is_active=is_active,
            all=all,
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
            pecan.abort(404, e.args[0])

    @wsme_pecan.wsexpose(mapping_models.Mapping,
                         bool,
                         body=mapping_models.Mapping,
                         status_code=201)
    def post(self, force=False, mapping_data=None):
        """Create a mapping.

        :param force: Allows start and end in the past.
        :param mapping_data: Informations about the mapping to create.
        """
        hashmap = db_api.get_instance()
        field_validations.validate_resource(
            mapping_data, force=force)
        try:
            created_by = get_request_user()
            mapping_db = hashmap.create_mapping(
                value=mapping_data.value,
                map_type=mapping_data.map_type,
                cost=mapping_data.cost,
                field_id=mapping_data.field_id,
                group_id=mapping_data.group_id,
                service_id=mapping_data.service_id,
                tenant_id=mapping_data.tenant_id,
                created_by=created_by,
                start=mapping_data.start,
                end=mapping_data.end,
                name=mapping_data.name,
                description=mapping_data.description)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += mapping_db.mapping_id
            return mapping_models.Mapping(
                **mapping_db.export_model())
        except db_api.MappingAlreadyExists as e:
            pecan.abort(409, e.args[0])
        except db_api.ClientHashMapError as e:
            pecan.abort(400, e.args[0])

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
            updated_by = get_request_user()
            current_mapping = hashmap.get_mapping(mapping_id)
            if field_validations.validate_update_allowing_only_end_date(
                    current_mapping,
                    mapping):
                hashmap.update_mapping(
                    mapping_id,
                    end=mapping.end,
                    updated_by=updated_by)
            else:
                hashmap.update_mapping(
                    mapping_id,
                    cost=mapping.cost,
                    start=mapping.start,
                    end=mapping.end,
                    updated_by=updated_by,
                    description=mapping.description)
            pecan.response.headers['Location'] = pecan.request.path
        except db_api.MappingAlreadyExists as e:
            pecan.abort(409, e.args[0])
        except db_api.NoSuchMapping as e:
            pecan.abort(404, e.args[0])
        except db_api.ClientHashMapError as e:
            pecan.abort(400, e.args[0])

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         status_code=204)
    def delete(self, mapping_id):
        """Delete a mapping.

        :param mapping_id: UUID of the mapping to delete.
        """
        hashmap = db_api.get_instance()
        deleted_by = get_request_user()
        try:
            hashmap.delete_mapping(mapping_id, deleted_by=deleted_by)
        except db_api.NoSuchMapping as e:
            pecan.abort(404, e.args[0])
