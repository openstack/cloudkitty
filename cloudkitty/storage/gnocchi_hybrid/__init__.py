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
import decimal

from oslo_log import log

from cloudkitty.storage.gnocchi_hybrid import migration
from cloudkitty.storage.gnocchi_hybrid import models
from cloudkitty.storage import sqlalchemy as sql_storage

LOG = log.getLogger(__name__)


class GnocchiHybridStorage(sql_storage.SQLAlchemyStorage):
    """Gnocchi Hybrid Storage Backend

    Driver used to add support for gnocchi until the creation of custom
    resources is supported in gnocchi.
    """
    frame_model = models.HybridRatedDataframe

    @staticmethod
    def init():
        migration.upgrade('head')

    def _append_time_frame(self, res_type, frame, tenant_id):
        rating_dict = frame.get('rating', {})
        rate = rating_dict.get('price')
        if not rate:
            rate = decimal.Decimal(0)
        resource_ref = frame.get('resource_id')
        if not resource_ref:
            LOG.warn('Trying to store data collected outside of gnocchi. '
                     'This driver can only be used with the gnocchi collector.'
                     ' Data not stored!')
            return
        self.add_time_frame(begin=self.usage_start_dt.get(tenant_id),
                            end=self.usage_end_dt.get(tenant_id),
                            tenant_id=tenant_id,
                            res_type=res_type,
                            resource_ref=resource_ref,
                            rate=rate)

    def add_time_frame(self, **kwargs):
        """Create a new time frame.

        :param begin: Start of the dataframe.
        :param end: End of the dataframe.
        :param res_type: Type of the resource.
        :param rate: Calculated rate for this dataframe.
        :param tenant_id: tenant_id of the dataframe owner.
        :param resource_ref: Reference to the gnocchi metric (UUID).
        """
        super(GnocchiHybridStorage, self).add_time_frame(**kwargs)
