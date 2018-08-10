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
import testtools

from cloudkitty.common import config as ck_config
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class ConfigTest(tests.TestCase):
    def test_config(self):
        ck_config.list_opts()
