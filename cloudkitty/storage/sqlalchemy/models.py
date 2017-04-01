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
import json

from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative

from cloudkitty import utils as ck_utils

Base = declarative.declarative_base()


class RatedDataFrame(Base, models.ModelBase):
    """A rated data frame.

    """
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    __tablename__ = 'rated_data_frames'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    tenant_id = sqlalchemy.Column(sqlalchemy.String(32),
                                  nullable=True)
    begin = sqlalchemy.Column(sqlalchemy.DateTime,
                              nullable=False)
    end = sqlalchemy.Column(sqlalchemy.DateTime,
                            nullable=False)
    unit = sqlalchemy.Column(sqlalchemy.String(255),
                             nullable=False)
    qty = sqlalchemy.Column(sqlalchemy.Numeric(15, 5),
                            nullable=False)
    res_type = sqlalchemy.Column(sqlalchemy.String(255),
                                 nullable=False)
    rate = sqlalchemy.Column(sqlalchemy.Float(),
                             nullable=False)
    desc = sqlalchemy.Column(sqlalchemy.Text(),
                             nullable=False)

    def to_cloudkitty(self, collector=None):
        # Rating informations
        rating_dict = {}
        rating_dict['price'] = self.rate

        # Volume informations
        vol_dict = {}
        vol_dict['qty'] = self.qty.normalize()
        vol_dict['unit'] = self.unit
        res_dict = {}

        # Encapsulate informations in a resource dict
        res_dict['rating'] = rating_dict
        res_dict['desc'] = json.loads(self.desc)
        res_dict['vol'] = vol_dict
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
