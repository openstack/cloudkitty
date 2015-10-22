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

from cloudkitty.tests.gabbi.fixtures import *  # noqa
from cloudkitty.rating.pyscripts.db import api as pyscripts_db


class PyScriptsConfigFixture(ConfigFixture):
    def start_fixture(self):
        super(PyScriptsConfigFixture, self).start_fixture()
        self.conn = pyscripts_db.get_instance()
        migration = self.conn.get_migration()
        migration.upgrade('head')
