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
from cloudkitty.rating.hash.datamodels import threshold as threshold_models
from cloudkitty.rating.hash.db import api as db_api


class HashMapGroupsController(rating.RatingRestControllerBase):
    """Controller responsible of groups management.

    """
    _custom_actions = {
        'mappings': ['GET'],
        'thresholds': ['GET']}

    @wsme_pecan.wsexpose(mapping_models.MappingCollection,
                         ck_types.UuidType())
    def mappings(self, group_id):
        """Get the mappings attached to the group.

        :param group_id: UUID of the group to filter on.
        """
        hashmap = db_api.get_instance()
        mapping_list = []
        mappings_uuid_list = hashmap.list_mappings(group_uuid=group_id)
        for mapping_uuid in mappings_uuid_list:
            mapping_db = hashmap.get_mapping(uuid=mapping_uuid)
            mapping_list.append(mapping_models.Mapping(
                **mapping_db.export_model()))
        res = mapping_models.MappingCollection(mappings=mapping_list)
        return res

    @wsme_pecan.wsexpose(threshold_models.ThresholdCollection,
                         ck_types.UuidType())
    def thresholds(self, group_id):
        """Get the thresholds attached to the group.

        :param group_id: UUID of the group to filter on.
        """
        hashmap = db_api.get_instance()
        threshold_list = []
        thresholds_uuid_list = hashmap.list_thresholds(group_uuid=group_id)
        for threshold_uuid in thresholds_uuid_list:
            threshold_db = hashmap.get_threshold(uuid=threshold_uuid)
            threshold_list.append(threshold_models.Threshold(
                **threshold_db.export_model()))
        res = threshold_models.ThresholdCollection(thresholds=threshold_list)
        return res

    @wsme_pecan.wsexpose(group_models.GroupCollection)
    def get_all(self):
        """Get the group list

        :return: List of every group.
        """
        hashmap = db_api.get_instance()
        group_list = []
        groups_uuid_list = hashmap.list_groups()
        for group_uuid in groups_uuid_list:
            group_db = hashmap.get_group(uuid=group_uuid)
            group_list.append(group_models.Group(
                **group_db.export_model()))
        res = group_models.GroupCollection(groups=group_list)
        return res

    @wsme_pecan.wsexpose(group_models.Group,
                         ck_types.UuidType())
    def get_one(self, group_id):
        """Return a group.

        :param group_id: UUID of the group to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            group_db = hashmap.get_group(uuid=group_id)
            return group_models.Group(**group_db.export_model())
        except db_api.NoSuchGroup as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(group_models.Group,
                         body=group_models.Group,
                         status_code=201)
    def post(self, group_data):
        """Create a group.

        :param group_data: Informations about the group to create.
        """
        hashmap = db_api.get_instance()
        try:
            group_db = hashmap.create_group(group_data.name)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += group_db.group_id
            return group_models.Group(
                **group_db.export_model())
        except db_api.GroupAlreadyExists as e:
            pecan.abort(409, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         bool,
                         status_code=204)
    def delete(self, group_id, recursive=False):
        """Delete a group.

        :param group_id: UUID of the group to delete.
        :param recursive: Delete mappings recursively.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.delete_group(uuid=group_id, recurse=recursive)
        except db_api.NoSuchGroup as e:
            pecan.abort(404, six.text_type(e))
