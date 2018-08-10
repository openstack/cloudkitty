# -*- coding: utf-8 -*-
# Copyright 2018 Objectif Libre
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
# @author: Luka Peschke
#
import testtools
from time import sleep

from gnocchiclient import exceptions as gexceptions
from oslo_log import log

from cloudkitty.tests.storage.v2 import base_functional
from cloudkitty.tests.utils import is_functional_test


LOG = log.getLogger(__name__)


@testtools.skipUnless(is_functional_test(), 'Test is not a functional test')
class GnocchiBaseFunctionalStorageTest(
        base_functional.BaseFunctionalStorageTest):

    storage_backend = 'gnocchi'
    storage_version = 2

    def setUp(self):
        super(GnocchiBaseFunctionalStorageTest, self).setUp()
        self.conf.import_group(
            'storage_gnocchi', 'cloudkitty.storage.v2.gnocchi')

    @classmethod
    def _get_status(cls):
        status = cls.storage._conn.status.get()
        return status['storage']['summary']['measures']

    @classmethod
    def wait_for_backend(cls):
        while True:
            status = cls._get_status()
            if status == 0:
                break
            LOG.info('Waiting for gnocchi to have processed all measures, {} '
                     'left.'.format(status))
            sleep(1)

    @classmethod
    def cleanup_backend(cls):
        for res_type in cls.storage._get_ck_resource_types():
            batch_query = {">=": {"started_at": "1970-01-01T01:00:00"}}
            cls.storage._conn.resource.batch_delete(
                batch_query, resource_type=res_type)
            try:
                cls.storage._conn.resource_type.delete(res_type)
            except gexceptions.BadRequest:
                pass
        try:
            cls.storage._conn.archive_policy.delete(
                'cloudkitty_archive_policy')
        except gexceptions.BadRequest:
            pass
