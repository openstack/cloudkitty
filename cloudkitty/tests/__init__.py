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
import testscenarios
import testtools

from cloudkitty.db import api as db_api


class TestCase(testscenarios.TestWithScenarios, testtools.TestCase):
    scenarios = [
        ('sqlite', dict(db_url='sqlite:///'))
    ]

    def setUp(self):
        super(TestCase, self).setUp()
        self.conf = self.useFixture(config_fixture.Config()).conf
        self.conf.set_override('connection', self.db_url, 'database')
        self.conn = db_api.get_instance()
        migration = self.conn.get_migration()
        migration.upgrade('head')
