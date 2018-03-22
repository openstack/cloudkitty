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
from cloudkitty.rating.hash.datamodels import threshold as threshold_models
from cloudkitty.rating.hash.db import api as db_api


class HashMapThresholdsController(rating.RatingRestControllerBase):
    """Controller responsible of thresholds management.

    """

    _custom_actions = {
        'group': ['GET']}

    @wsme_pecan.wsexpose(group_models.Group,
                         ck_types.UuidType())
    def group(self, threshold_id):
        """Get the group attached to the threshold.

        :param threshold_id: UUID of the threshold to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            group_db = hashmap.get_group_from_threshold(
                uuid=threshold_id)
            return group_models.Group(**group_db.export_model())
        except db_api.ThresholdHasNoGroup as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(threshold_models.ThresholdCollection,
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
        """Get the threshold list

        :param service_id: Service UUID to filter on.
        :param field_id: Field UUID to filter on.
        :param group_id: Group UUID to filter on.
        :param no_group: Filter on orphaned thresholds.
        :param tenant_id: Tenant UUID to filter on.
        :param filter_tenant: Explicitly filter on tenant (default is to not
        filter on tenant). Useful if you want to filter on tenant being None.
        :return: List of every thresholds.
        """
        hashmap = db_api.get_instance()
        threshold_list = []
        search_opts = dict()
        if filter_tenant:
            search_opts['tenant_uuid'] = tenant_id
        thresholds_uuid_list = hashmap.list_thresholds(
            service_uuid=service_id,
            field_uuid=field_id,
            group_uuid=group_id,
            no_group=no_group,
            **search_opts)
        for threshold_uuid in thresholds_uuid_list:
            threshold_db = hashmap.get_threshold(uuid=threshold_uuid)
            threshold_list.append(threshold_models.Threshold(
                **threshold_db.export_model()))
        res = threshold_models.ThresholdCollection(thresholds=threshold_list)
        return res

    @wsme_pecan.wsexpose(threshold_models.Threshold,
                         ck_types.UuidType())
    def get_one(self, threshold_id):
        """Return a threshold.

        :param threshold_id: UUID of the threshold to filter on.
        """
        hashmap = db_api.get_instance()
        try:
            threshold_db = hashmap.get_threshold(uuid=threshold_id)
            return threshold_models.Threshold(
                **threshold_db.export_model())
        except db_api.NoSuchThreshold as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(threshold_models.Threshold,
                         body=threshold_models.Threshold,
                         status_code=201)
    def post(self, threshold_data):
        """Create a threshold.

        :param threshold_data: Informations about the threshold to create.
        """
        hashmap = db_api.get_instance()
        try:
            threshold_db = hashmap.create_threshold(
                level=threshold_data.level,
                map_type=threshold_data.map_type,
                cost=threshold_data.cost,
                field_id=threshold_data.field_id,
                group_id=threshold_data.group_id,
                service_id=threshold_data.service_id,
                tenant_id=threshold_data.tenant_id)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += threshold_db.threshold_id
            return threshold_models.Threshold(
                **threshold_db.export_model())
        except db_api.ThresholdAlreadyExists as e:
            pecan.abort(409, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         body=threshold_models.Threshold,
                         status_code=302)
    def put(self, threshold_id, threshold):
        """Update a threshold.

        :param threshold_id: UUID of the threshold to update.
        :param threshold: Threshold data to insert.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.update_threshold(
                threshold_id,
                threshold_id=threshold.threshold_id,
                level=threshold.level,
                cost=threshold.cost,
                map_type=threshold.map_type,
                group_id=threshold.group_id,
                tenant_id=threshold.tenant_id)
            pecan.response.headers['Location'] = pecan.request.path
        except db_api.NoSuchThreshold as e:
            pecan.abort(404, six.text_type(e))
        except db_api.ClientHashMapError as e:
            pecan.abort(400, six.text_type(e))

    @wsme_pecan.wsexpose(None,
                         ck_types.UuidType(),
                         status_code=204)
    def delete(self, threshold_id):
        """Delete a threshold.

        :param threshold_id: UUID of the threshold to delete.
        """
        hashmap = db_api.get_instance()
        try:
            hashmap.delete_threshold(uuid=threshold_id)
        except db_api.NoSuchThreshold as e:
            pecan.abort(404, six.text_type(e))
