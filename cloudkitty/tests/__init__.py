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
# @author: Gauvain Pocentek
#
from oslo.config import fixture as config_fixture
from oslotest import base
import testscenarios

from cloudkitty import db
from cloudkitty.db import api as ck_db_api
from cloudkitty import rating


class FakeRatingModule(rating.RatingProcessorBase):
    module_name = 'fake'
    description = 'fake rating module'

    def __init__(self, tenant_id=None):
        super(FakeRatingModule, self).__init__()

    def quote(self, data):
        self.process(data)

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service in cur_usage:
                for entry in cur_usage[service]:
                    if 'rating' not in entry:
                        entry['rating'] = {'price': 0}
        return data

    def reload_config(self):
        pass

    def notify_reload(self):
        pass


class TestCase(testscenarios.TestWithScenarios, base.BaseTestCase):
    scenarios = [
        ('sqlite', dict(db_url='sqlite:///'))
    ]

    def setUp(self):
        super(TestCase, self).setUp()
        self.conf = self.useFixture(config_fixture.Config()).conf
        self.conf.set_override('connection', self.db_url, 'database')
        self.conn = ck_db_api.get_instance()
        migration = self.conn.get_migration()
        migration.upgrade('head')

    def tearDown(self):
        db.get_engine().dispose()
        super(TestCase, self).tearDown()
