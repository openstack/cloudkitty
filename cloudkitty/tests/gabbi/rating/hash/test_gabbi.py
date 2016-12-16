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
import os

from gabbi import driver

from cloudkitty.tests.gabbi import fixtures
from cloudkitty.tests.gabbi import handlers as cloudkitty_handlers
from cloudkitty.tests.gabbi.rating.hash import fixtures as hash_fixtures

TESTS_DIR = 'gabbits'


def load_tests(loader, tests, pattern):
    test_dir = os.path.join(os.path.dirname(__file__), TESTS_DIR)
    return driver.build_tests(test_dir,
                              loader,
                              host=None,
                              intercept=fixtures.setup_app,
                              fixture_module=hash_fixtures,
                              response_handlers=[
                                  cloudkitty_handlers.EnvironStoreHandler])
