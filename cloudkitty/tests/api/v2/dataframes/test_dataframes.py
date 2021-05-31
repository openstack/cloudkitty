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
import flask

from unittest import mock

from cloudkitty.api.v2.dataframes import dataframes
from cloudkitty import tests

from cloudkitty.utils import tz as tzutils


class TestDataframeListEndpoint(tests.TestCase):

    def setUp(self):
        super(TestDataframeListEndpoint, self).setUp()
        self.endpoint = dataframes.DataFrameList()

    def test_non_admin_request_is_filtered_on_project_id(self):
        policy_mock = mock.patch('cloudkitty.common.policy.authorize')

        flask.request.context = mock.Mock()
        flask.request.context.project_id = 'test-project'
        flask.request.context.is_admin = False

        with mock.patch.object(self.endpoint._storage, 'retrieve') as ret_mock:
            with policy_mock, mock.patch('flask.request.args.lists') as fmock:
                ret_mock.return_value = {'total': 42, 'dataframes': []}
                fmock.return_value = []
                self.endpoint.get()
                ret_mock.assert_called_once_with(
                    begin=tzutils.get_month_start(),
                    end=tzutils.get_next_month(),
                    metric_types=None,
                    filters={'project_id': 'test-project'},
                    offset=0,
                    limit=100,
                )
