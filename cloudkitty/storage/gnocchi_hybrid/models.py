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
from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative

from cloudkitty import utils as ck_utils

Base = declarative.declarative_base()


class HybridRatedDataframe(Base, models.ModelBase):
    """An hybrid rated dataframe.

    """
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    __tablename__ = 'ghybrid_dataframes'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    begin = sqlalchemy.Column(sqlalchemy.DateTime,
                              nullable=False)
    end = sqlalchemy.Column(sqlalchemy.DateTime,
                            nullable=False)
    res_type = sqlalchemy.Column(sqlalchemy.String(255),
                                 nullable=False)
    rate = sqlalchemy.Column(sqlalchemy.Numeric(20, 8),
                             nullable=False)
    resource_ref = sqlalchemy.Column(sqlalchemy.String(32),
                                     nullable=False)
    tenant_id = sqlalchemy.Column(sqlalchemy.String(32),
                                  nullable=True)

    def to_cloudkitty(self, collector=None):
        if not collector:
            raise Exception('Gnocchi storage needs a reference '
                            'to the collector.')
        # Rating informations
        rating_dict = {}
        rating_dict['price'] = self.rate

        # Resource information from gnocchi
        resource_data = collector.resource_info(
            resource_type=self.res_type,
            start=self.begin,
            end=self.end,
            resource_id=self.resource_ref,
            project_id=self.tenant_id)

        # Encapsulate informations in a resource dict
        res_dict = {}
        res_dict['desc'] = resource_data['desc']
        res_dict['vol'] = resource_data['vol']
        res_dict['rating'] = rating_dict
        res_dict['tenant_id'] = self.tenant_id

        # Add resource to the usage dict
        usage_dict = {}
        usage_dict[self.res_type] = [res_dict]

        # Time informations
        period_dict = {}
        period_dict['begin'] = ck_utils.dt2iso(self.begin)
        period_dict['end'] = ck_utils.dt2iso(self.end)

        # Add period to the resource informations
        ck_dict = {}
        ck_dict['period'] = period_dict
        ck_dict['usage'] = usage_dict
        return ck_dict
