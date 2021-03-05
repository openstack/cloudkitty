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
import uuid

from unittest import mock
import voluptuous

from cloudkitty.api.v2.summary import summary
from cloudkitty import tests

from cloudkitty.utils import tz as tzutils


class TestSummaryEndpoint(tests.TestCase):

    def setUp(self):
        super(TestSummaryEndpoint, self).setUp()
        self.endpoint = summary.Summary()

    def test_type_filter_is_passed_separately(self):
        policy_mock = mock.patch('cloudkitty.common.policy.authorize')

        flask.request.context = mock.Mock()
        flask.request.context.project_id = str(uuid.uuid4())
        flask.request.context.is_admin = True

        with mock.patch.object(self.endpoint._storage, 'total') as total_mock:
            with policy_mock, mock.patch('flask.request.args.lists') as fmock:
                total_mock.return_value = {'total': 0, 'results': []}
                fmock.return_value = [
                    ('filters', 'a:b,type:awesome')]
                self.endpoint.get()
                total_mock.assert_called_once_with(
                    begin=tzutils.get_month_start(),
                    end=tzutils.get_next_month(),
                    groupby=None,
                    filters={'a': ['b']},
                    metric_types=['awesome'],
                    offset=0,
                    limit=100,
                    paginate=True,
                )

    def test_invalid_response_type(self):
        self.assertRaises(voluptuous.Invalid, self.endpoint.get,
                          response_format="INVALID_RESPONSE_TYPE")

    def test_generate_response_table_response_type(self):
        objects = [{"a1": "obj1", "a2": "value1"},
                   {"a1": "obj2", "a2": "value2"}]

        total = {'total': len(objects),
                 'results': objects}

        response = self.endpoint.generate_response(
            summary.TABLE_RESPONSE_FORMAT, total)

        self.assertIn('total', response)
        self.assertIn('results', response)
        self.assertIn('columns', response)

        self.assertEqual(len(objects), response['total'])
        self.assertEqual(list(objects[0].keys()), response['columns'])
        self.assertEqual(
            [list(res.values()) for res in objects], response['results'])
        self.assertEqual(summary.TABLE_RESPONSE_FORMAT, response['format'])

    def test_generate_response_object_response_type(self):
        objects = [{"a1": "obj1", "a2": "value1"},
                   {"a1": "obj2", "a2": "value2"}]

        total = {'total': len(objects),
                 'results': objects}

        response = self.endpoint.generate_response(
            summary.OBJECT_RESPONSE_FORMAT, total)

        self.assertIn('total', response)
        self.assertIn('results', response)
        self.assertNotIn('columns', response)

        self.assertEqual(len(objects), response['total'])
        self.assertEqual(objects, response['results'])
        self.assertEqual(summary.OBJECT_RESPONSE_FORMAT, response['format'])
