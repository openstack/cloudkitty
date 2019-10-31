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
import datetime

from oslo_config import cfg
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import storage as storage_models
from cloudkitty.common import policy
from cloudkitty import storage
from cloudkitty.utils import tz as tzutils


CONF = cfg.CONF

CONF.import_opt('scope_key', 'cloudkitty.collector', 'collect')


class DataFramesController(rest.RestController):
    """REST Controller to access stored data frames."""

    @wsme_pecan.wsexpose(storage_models.DataFrameCollection,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text,
                         wtypes.text)
    def get_all(self, begin=None, end=None, tenant_id=None,
                resource_type=None):
        """Return a list of rated resources for a time period and a tenant.

        :param begin: Start of the period
        :param end: End of the period
        :param tenant_id: UUID of the tenant to filter on.
        :param resource_type: Type of the resource to filter on.
        :return: Collection of DataFrame objects.
        """

        project_id = tenant_id or pecan.request.context.project_id
        policy.authorize(pecan.request.context, 'storage:list_data_frames', {
            'project_id': project_id,
        })

        scope_key = CONF.collect.scope_key
        backend = pecan.request.storage_backend
        dataframes = []
        if pecan.request.context.is_admin:
            filters = {scope_key: tenant_id} if tenant_id else None
        else:
            # Unscoped non-admin user
            if project_id is None:
                return {'dataframes': []}
            filters = {scope_key: project_id}
        try:
            resp = backend.retrieve(
                begin, end,
                filters=filters,
                metric_types=resource_type,
                paginate=False)
        except storage.NoTimeFrame:
            return storage_models.DataFrameCollection(dataframes=[])
        for frame in resp['dataframes']:
            frame_tenant = None
            for type_, points in frame.itertypes():
                resources = []
                for point in points:
                    resource = storage_models.RatedResource(
                        service=type_,
                        desc=point.desc,
                        volume=point.qty,
                        rating=point.price)
                    if frame_tenant is None:
                        # NOTE(jferrieu): Since DataFrame/DataPoint
                        # implementation patch we cannot guarantee
                        # anymore that a DataFrame does contain a scope_id
                        # therefore the __UNDEF__ default value has been
                        # retained to maintain backward compatibility
                        # if it would occur being absent
                        frame_tenant = point.desc.get(scope_key, '__UNDEF__')
                    resources.append(resource)
                dataframe = storage_models.DataFrame(
                    begin=tzutils.local_to_utc(frame.start, naive=True),
                    end=tzutils.local_to_utc(frame.end, naive=True),
                    tenant_id=frame_tenant,
                    resources=resources)
                dataframes.append(dataframe)
        return storage_models.DataFrameCollection(dataframes=dataframes)


class StorageController(rest.RestController):
    """REST Controller to access stored data."""

    dataframes = DataFramesController()
