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
from oslo_upgradecheck import upgradecheck

from cloudkitty.cli import status
from cloudkitty import tests


class CloudKittyStatusCheckUpgradeTest(tests.TestCase):

    def setUp(self):
        super(CloudKittyStatusCheckUpgradeTest, self).setUp()
        self._checks = status.CloudkittyUpgradeChecks()

    def test_storage_version_with_v1(self):
        self.conf.set_override('version', 1, 'storage')
        self.assertEqual(
            upgradecheck.Code.WARNING,
            self._checks._storage_version().code,
        )

    def test_storage_version_with_v2(self):
        self.conf.set_override('version', 2, 'storage')
        self.assertEqual(
            upgradecheck.Code.SUCCESS,
            self._checks._storage_version().code,
        )
