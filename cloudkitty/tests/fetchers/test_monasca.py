# Copyright 2019 Objectif Libre
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

from unittest import mock

from cloudkitty.fetcher import monasca as mon_fetcher
from cloudkitty import tests


class MonascaFetcherTest(tests.TestCase):

    def setUp(self):
        super(MonascaFetcherTest, self).setUp()
        self.conf.set_override('dimension_name', 'dimension_name_test',
                               'fetcher_monasca')
        self.conf.set_override('monasca_tenant_id', 'this_is_definitely_a_uid',
                               'fetcher_monasca')
        self.conf.set_override('monasca_service_name', 'monasca-api-test',
                               'fetcher_monasca')
        self.conf.set_override('interface', 'interface-test',
                               'fetcher_monasca')

        with mock.patch(
                'cloudkitty.common.monasca_client.'
                'get_monasca_endpoint',
                return_value='http://noop'):
            self.fetcher = mon_fetcher.MonascaFetcher()

    def test_get_tenants(self):
        with mock.patch.object(self.fetcher._conn.metrics,
                               'list_dimension_values') as m:
            self.fetcher.get_tenants()
            m.assert_called_once_with(
                tenant_id='this_is_definitely_a_uid',
                dimension_name='dimension_name_test',
            )
