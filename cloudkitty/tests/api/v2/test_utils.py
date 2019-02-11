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
import flask
import mock
import voluptuous
from werkzeug.exceptions import BadRequest

from cloudkitty.api.v2 import utils as api_utils
from cloudkitty import tests


class ApiUtilsDoInitTest(tests.TestCase):

    def test_do_init_valid_app_and_resources(self):
        app = flask.Flask('cloudkitty')
        resources = [
            {
                'module': 'cloudkitty.api.v2.example.example',
                'resource_class': 'Example',
                'url': '/example',
            },
        ]
        api_utils.do_init(app, 'example', resources)

    def test_do_init_invalid_resource(self):
        app = flask.Flask('cloudkitty')
        resources = [
            {
                'module': 'cloudkitty.api.v2.invalid',
                'resource_class': 'Invalid',
                'url': '/invalid',
            },
        ]
        self.assertRaises(
            api_utils.ResourceNotFound,
            api_utils.do_init,
            app, 'invalid', resources,
        )


class SingleQueryParamTest(tests.TestCase):

    def test_single_int_to_int(self):
        self.assertEqual(api_utils.SingleQueryParam(int)(42), 42)

    def test_single_str_to_int(self):
        self.assertEqual(api_utils.SingleQueryParam(str)(42), '42')

    def test_int_list_to_int(self):
        self.assertEqual(api_utils.SingleQueryParam(int)([42]), 42)

    def test_str_list_to_int(self):
        self.assertEqual(api_utils.SingleQueryParam(str)([42]), '42')

    def test_raises_length_invalid_empty_list(self):
        validator = api_utils.SingleQueryParam(int)
        self.assertRaises(
            voluptuous.LengthInvalid,
            validator,
            [],
        )

    def test_raises_length_invalid_long_list(self):
        validator = api_utils.SingleQueryParam(int)
        self.assertRaises(
            voluptuous.LengthInvalid,
            validator,
            [0, 1],
        )


class AddInputSchemaTest(tests.TestCase):

    def test_paginated(self):

        @api_utils.paginated
        def test_func(self, offset=None, limit=None):
            self.assertEqual(offset, 0)
            self.assertEqual(limit, 100)

        self.assertIn('offset', test_func.input_schema.schema.keys())
        self.assertIn('limit', test_func.input_schema.schema.keys())
        self.assertEqual(2, len(test_func.input_schema.schema.keys()))

        with mock.patch('flask.request') as m:
            m.args = {}
            test_func(self)
            m.args = {'offset': 0, 'limit': 100}
            test_func(self)

            m.args = {'offset': 1}
            self.assertRaises(AssertionError, test_func, self)
            m.args = {'limit': 99}
            self.assertRaises(AssertionError, test_func, self)
            m.args = {'offset': -1}
            self.assertRaises(BadRequest, test_func, self)
            m.args = {'limit': 0}
            self.assertRaises(BadRequest, test_func, self)

    def test_simple_add_input_schema_query(self):

        @api_utils.add_input_schema('query', {
            voluptuous.Required(
                'arg_one', default='one'): api_utils.SingleQueryParam(str),
        })
        def test_func(self, arg_one=None):
            self.assertEqual(arg_one, 'one')

        self.assertEqual(len(test_func.input_schema.schema.keys()), 1)
        self.assertEqual(
            list(test_func.input_schema.schema.keys())[0], 'arg_one')

        with mock.patch('flask.request') as m:
            m.args = {}
            test_func(self)
            m.args = {'arg_one': 'one'}
            test_func(self)

    def test_simple_add_input_schema_body(self):

        @api_utils.add_input_schema('body', {
            voluptuous.Required(
                'arg_one', default='one'): api_utils.SingleQueryParam(str),
        })
        def test_func(self, arg_one=None):
            self.assertEqual(arg_one, 'one')

        self.assertEqual(len(test_func.input_schema.schema.keys()), 1)
        self.assertEqual(
            list(test_func.input_schema.schema.keys())[0], 'arg_one')

        with mock.patch('flask.request') as m:
            m.get_json.return_value = {}
            test_func(self)

        with mock.patch('flask.request') as m:
            m.get_json.return_value = {'arg_one': 'one'}
            test_func(self)

    def _test_multiple_add_input_schema_x(self, location):

        @api_utils.add_input_schema(location, {
            voluptuous.Required(
                'arg_one', default='one'):
            api_utils.SingleQueryParam(str) if location == 'query' else str,
        })
        @api_utils.add_input_schema(location, {
            voluptuous.Required(
                'arg_two', default='two'):
            api_utils.SingleQueryParam(str) if location == 'query' else str,
        })
        def test_func(self, arg_one=None, arg_two=None):
            self.assertEqual(arg_one, 'one')
            self.assertEqual(arg_two, 'two')

        self.assertEqual(len(test_func.input_schema.schema.keys()), 2)
        self.assertEqual(
            sorted(list(test_func.input_schema.schema.keys())),
            ['arg_one', 'arg_two'],
        )

    def test_multiple_add_input_schema_query(self):
        self._test_multiple_add_input_schema_x('query')

    def test_multiple_add_input_schema_body(self):
        self._test_multiple_add_input_schema_x('body')
