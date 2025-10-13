# Copyright 2025 Red Hat
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

from datetime import datetime
from datetime import timezone
import json
import unittest
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

from cloudkitty.storage.v2.loki import client
from cloudkitty.storage.v2.loki import exceptions


class MockDataPoint:
    def __init__(self, unit="USD/h", description="desc", qty=1.0, price=10.0,
                 groupby=None, metadata=None):
        self.unit = unit
        self.description = description
        self.qty = qty
        self.price = price
        self.groupby = groupby if groupby is not None \
            else {'project_id': 'proj1'}
        self.metadata = metadata if metadata is not None \
            else {'meta_key': 'meta_val'}


@patch('cloudkitty.storage.v2.loki.client.requests', autospec=True)
@patch('cloudkitty.storage.v2.loki.client.LOG', autospec=True)
class TestLokiClient(unittest.TestCase):

    def setUp(self):
        self.base_url = "http://loki:3100/loki/api/v1"
        self.tenant = "test_tenant"
        self.stream_labels = {"app": "cloudkitty", "source": "test"}
        self.content_type = "application/json"
        self.buffer_size = 2
        self.cert = ('/path/to/cert', '/path/to/key')
        self.verify = '/path/to/cafile'
        self.client = client.LokiClient(
            self.base_url,
            self.tenant,
            self.stream_labels,
            self.content_type,
            self.buffer_size,
            cert=self.cert,
            verify=self.verify
        )
        self.begin_dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.end_dt = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    def test_init_success(self, mock_log, mock_requests):
        self.assertEqual(self.client._base_url, self.base_url)
        self.assertEqual(self.client._stream_labels, self.stream_labels)
        self.assertEqual(self.client._headers['X-Scope-OrgID'], self.tenant)
        self.assertEqual(self.client._headers['Content-Type'],
                         self.content_type)
        self.assertEqual(self.client._buffer_size, self.buffer_size)
        self.assertEqual(self.client._points, [])
        self.assertEqual(self.client._cert, self.cert)
        self.assertEqual(self.client._verify, self.verify)

    def test_init_unsupported_content_type(self, mock_log, mock_requests):
        with self.assertRaises(exceptions.UnsupportedContentType):
            client.LokiClient(self.base_url, self.tenant, self.stream_labels,
                              "text/plain", self.buffer_size, None, True)

    def test_build_payload_json(self, mock_log, mock_requests):
        batch = [["1609459200000000000", "log line 1"],
                 ["1609459200000000001", "log line 2"]]
        payload = self.client._build_payload_json(batch)
        expected_payload = {
            "streams": [
                {
                    "stream": self.stream_labels,
                    "values": batch
                }
            ]
        }
        self.assertEqual(payload, expected_payload)

    def test_dict_to_loki_query(self, mock_log, mock_requests):
        self.assertEqual(self.client._dict_to_loki_query({}), '{}')
        self.assertEqual(self.client._dict_to_loki_query({"foo": "bar"}),
                         '{foo="bar"}')
        self.assertEqual(
            self.client._dict_to_loki_query({"foo": "bar", "baz": "qux"}),
            '{foo="bar", baz="qux"}'
        )
        self.assertIn('foo="bar"', self.client._dict_to_loki_query(
            {"foo": "bar", "baz": "qux"}))
        self.assertIn('baz="qux"', self.client._dict_to_loki_query(
            {"foo": "bar", "baz": "qux"}))
        self.assertEqual(
            self.client._dict_to_loki_query({"foo": ["bar", "baz"]}),
            '{foo="bar"}'
        )
        self.assertEqual(
            self.client._dict_to_loki_query({"path": "/api/v1"}),
            '{path="/api/v1"}'
        )
        self.assertEqual(
            self.client._dict_to_loki_query({"msg": 'hello "world"'}),
            '{msg="hello \\"world\\""}'
        )
        self.assertEqual(
            self.client._dict_to_loki_query({"foo": "bar"}, groupby=True),
            '{groupby_foo="bar"}'
        )
        self.assertEqual(
            self.client._dict_to_loki_query({"foo": "bar"}, brackets=False),
            'foo="bar"'
        )
        self.assertEqual(
            self.client._dict_to_loki_query(
                {"foo": "bar", "baz": "qux"}, brackets=False
            ),
            'foo="bar", baz="qux"'
        )

    def test_base_query(self, mock_log, mock_requests):
        expected_query = (self.client._dict_to_loki_query(self.stream_labels)
                          + ' | json')
        self.assertEqual(self.client._base_query(), expected_query)

    def test_search_success(self, mock_log, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "resultType": "streams",
                "result": [{"stream": {}, "values": []}]
            }
        }
        mock_requests.get.return_value = mock_response
        query = '{app="test"} | json'
        data = self.client.search(query, self.begin_dt, self.end_dt, 100)
        expected_url = f"{self.base_url}/query_range"
        expected_params = {
            "query": query,
            "start": int(self.begin_dt.timestamp() * 1_000_000_000),
            "end": int(self.end_dt.timestamp() * 1_000_000_000),
            "limit": 100
        }
        mock_requests.get.assert_called_once_with(
            expected_url,
            params=expected_params,
            headers=self.client._headers,
            cert=self.client._cert,
            verify=self.client._verify
        )
        self.assertEqual(
            data,
            {"resultType": "streams", "result": [{"stream": {}, "values": []}]}
        )

    def test_search_no_query_uses_base_query(self, mock_log, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}
        mock_requests.get.return_value = mock_response
        self.client.search(None, self.begin_dt, self.end_dt, 100)
        expected_query = self.client._base_query()
        mock_requests.get.assert_called_once()
        _called_args, called_kwargs = mock_requests.get.call_args
        self.assertEqual(called_kwargs['params']['query'], expected_query)
        self.assertEqual(called_kwargs['cert'], self.client._cert)
        self.assertEqual(called_kwargs['verify'], self.client._verify)

    def test_search_failure(self, mock_log, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.get.return_value = mock_response
        query = '{app="test"} | json'
        data = self.client.search(query, self.begin_dt, self.end_dt, 100)
        self.assertEqual(data, [])
        expected_msg = ("Failed to query logs or empty result: 500 - "
                        "Internal Server Error")
        mock_log.error.assert_called_once_with(expected_msg)

    def test_push_success_batch(self, mock_log, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_requests.post.return_value = mock_response
        self.client._points = [["ts1", "log1"], ["ts2", "log2"]]
        self.client.push()
        expected_url = f"{self.base_url}/push"
        expected_payload = self.client._build_payload_json(
            [["ts1", "log1"], ["ts2", "log2"]]
        )
        mock_requests.post.assert_called_once_with(
            expected_url, json=expected_payload, headers=self.client._headers,
            cert=self.client._cert, verify=self.client._verify
        )
        self.assertEqual(self.client._points, [])
        log_msg = "Batch of 2 messages pushed successfully."
        mock_log.debug.assert_called_once_with(log_msg)

    def test_push_failure(self, mock_log, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response
        initial_points = [["ts1", "log1"], ["ts2", "log2"]]
        self.client._points = list(initial_points)
        self.client.push()
        self.assertEqual(self.client._points, initial_points)
        expected_msg = "Failed to push logs: 400 - Bad Request"
        mock_log.error.assert_called_once_with(expected_msg)
        mock_requests.post.assert_called_once_with(
            f"{self.base_url}/push",
            json=self.client._build_payload_json(initial_points),
            headers=self.client._headers,
            cert=self.client._cert,
            verify=self.client._verify
        )

    def test_push_no_points(self, mock_log, mock_requests):
        self.client._points = []
        self.client.push()
        mock_requests.post.assert_not_called()

    @patch.object(client.LokiClient, 'search')
    def test_retrieve_no_filters_no_metric_types(self, mock_search, mock_log,
                                                 mock_requests_arg):
        mock_search_result = {
            "stats": {"summary": {"totalEntriesReturned": 5}},
            "result": [{"stream": {}, "values": [["ts", '{"key":"val"}']]}]
        }
        mock_search.return_value = mock_search_result
        total, output = self.client.retrieve(self.begin_dt, self.end_dt,
                                             None, None, 100)
        expected_base_query = self.client._base_query()
        mock_search.assert_called_once_with(
            expected_base_query, self.begin_dt, self.end_dt, 100
        )
        self.assertEqual(total, 5)
        self.assertEqual(output, mock_search_result["result"])

    @patch.object(client.LokiClient, 'search')
    def test_retrieve_with_filters_and_metric_type_string(
            self, mock_search, mock_log, mock_requests_arg):
        mock_search_result = {
            "stats": {"summary": {"totalEntriesReturned": 2}},
            "result": [{"stream": {}, "values": [["ts", '{"type":"t1"}']]}]
        }
        mock_search.return_value = mock_search_result
        filters = {"project_id": "proj1", "region": "reg1"}
        metric_types = "cpu_util"
        total, output = self.client.retrieve(self.begin_dt, self.end_dt,
                                             filters, metric_types, 50)
        base_query = self.client._base_query()
        filter_query_part = self.client._dict_to_loki_query(
            filters, groupby=True, brackets=False
        )
        metric_query_part = f'type = "{metric_types}"'
        expected_full_query = (
            f"{base_query} | {filter_query_part}, {metric_query_part}"
        )
        mock_search.assert_called_once_with(
            expected_full_query, self.begin_dt, self.end_dt, 50
        )
        self.assertEqual(total, 2)
        self.assertEqual(output, mock_search_result["result"])

    @patch.object(client.LokiClient, 'search')
    def test_retrieve_with_metric_type_list(self, mock_search, mock_log,
                                            mock_requests_arg):
        mock_search.return_value = {
            "stats": {"summary": {"totalEntriesReturned": 1}},
            "result": ["data"]
        }
        metric_types = ["cpu_util", "ram_util"]
        self.client.retrieve(self.begin_dt, self.end_dt, None,
                             metric_types, 50)
        base_query = self.client._base_query()
        metric_query_part = f'type = "{metric_types[0]}"'
        expected_full_query = f"{base_query} | {metric_query_part}"
        mock_search.assert_called_once_with(
            expected_full_query, self.begin_dt, self.end_dt, 50
        )

    @patch.object(client.LokiClient, 'search')
    def test_retrieve_empty_or_malformed_search_response(
            self, mock_search, mock_loki_client_log, mock_requests_arg):
        mock_search.return_value = []
        expected_query_for_log = self.client._base_query()
        total, output = self.client.retrieve(self.begin_dt, self.end_dt,
                                             None, None, 100)
        self.assertEqual(total, 0)
        self.assertEqual(output, [])
        expected_log_message_case1 = (
            f"Data from Loki search is not in the expected dictionary format "
            f"or is missing keys. Query: '{expected_query_for_log}'. "
            f"Response received: {mock_search.return_value}"
        )
        mock_loki_client_log.warning.assert_called_with(
            expected_log_message_case1
        )
        mock_search.reset_mock()
        mock_loki_client_log.reset_mock()
        mock_search.return_value = {"nodata": True}
        total, output = self.client.retrieve(self.begin_dt, self.end_dt,
                                             None, None, 100)
        self.assertEqual(total, 0)
        self.assertEqual(output, [])
        expected_log_message_case2 = (
            f"Data from Loki search is not in the expected dictionary format "
            f"or is missing keys. Query: '{expected_query_for_log}'. "
            f"Response received: {mock_search.return_value}"
        )
        mock_loki_client_log.warning.assert_called_with(
            expected_log_message_case2
        )

    @patch.object(client.LokiClient, 'push')
    def test_add_point_no_push(self, mock_push, mock_log,
                               mock_requests_arg):
        self.client._buffer_size = 3
        point = MockDataPoint(qty=1, price=10)
        self.client.add_point(point, "test_type", self.begin_dt, self.end_dt)
        self.assertEqual(len(self.client._points), 1)
        added_point_data = json.loads(self.client._points[0][1])
        self.assertEqual(added_point_data['type'], "test_type")
        self.assertEqual(added_point_data['qty'], 1)
        self.assertEqual(added_point_data['price'], 10)
        self.assertEqual(added_point_data['start'],
                         "2024-01-01T00:00:00+00:00")
        self.assertEqual(added_point_data['end'], "2024-01-01T01:00:00+00:00")
        self.assertEqual(added_point_data['groupby'], point.groupby)
        mock_push.assert_not_called()

    @patch.object(client.LokiClient, 'push')
    def test_add_point_triggers_push(self, mock_push, mock_log,
                                     mock_requests_arg):
        self.client._buffer_size = 1
        point = MockDataPoint()
        self.client.add_point(point, "test_type", self.begin_dt, self.end_dt)
        self.assertEqual(len(self.client._points), 1)
        mock_push.assert_called_once()

    @patch.object(client.LokiClient, 'retrieve')
    def test_total_no_groupby(self, mock_retrieve, mock_log,
                              mock_requests_arg):
        loki_data_for_total = [
            {
                "stream": {"groupby_project_id": "p1", "type": "t1",
                           "qty": "10.0", "price": "100.0"},
                "values": [["ts1", json.dumps(
                    {"qty": 10.0, "price": 100.0, "type": "t1",
                     "groupby": {"project_id": "p1"}})]]
            },
            {
                "stream": {"groupby_project_id": "p1", "type": "t1",
                           "qty": "5.0", "price": "50.0"},
                "values": [["ts2", json.dumps(
                    {"qty": 5.0, "price": 50.0, "type": "t1",
                     "groupby": {"project_id": "p1"}})]]
            },
        ]
        mock_retrieve.return_value = (2, loki_data_for_total)
        count, result = self.client.total(
            self.begin_dt, self.end_dt, "some_type", None, None,
            None, 0, 100, False
        )
        mock_retrieve.assert_called_once_with(
            self.begin_dt, self.end_dt, None, "some_type", 100
        )
        self.assertEqual(count, 1)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['sum_qty']['value'], 15.0)
        self.assertAlmostEqual(result[0]['sum_price']['value'], 150.0)
        mock_log.warning.assert_not_called()

    @patch.object(client.LokiClient, 'retrieve')
    def test_total_with_groupby(self, mock_retrieve, mock_log,
                                mock_requests_arg):
        loki_data_for_total = [
            {
                "stream": {"groupby_project_id": "proj1", "type": "typeA",
                           "qty": 10.0, "price": 100.0},
                "values": [["ts1", json.dumps(
                    {"qty": 10.0, "price": 100.0, "type": "typeA",
                     "groupby": {"project_id": "proj1"}})]
                ]
            },
            {
                "stream": {"groupby_project_id": "proj1", "type": "typeB",
                           "qty": 5.0, "price": 50.0},
                "values": [["ts2", json.dumps(
                    {"qty": 5.0, "price": 50.0, "type": "typeB",
                     "groupby": {"project_id": "proj1"}})]
                ]
            },
            {
                "stream": {"groupby_project_id": "proj2", "type": "typeA",
                           "qty": 2.0, "price": 20.0},
                "values": [["ts3", json.dumps(
                    {"qty": 2.0, "price": 20.0, "type": "typeA",
                     "groupby": {"project_id": "proj2"}})]
                ]
            },
            {
                "stream": {"groupby_project_id": "proj1", "type": "typeA",
                           "qty": 8.0, "price": 80.0},
                "values": [["ts4", json.dumps(
                    {"qty": 8.0, "price": 80.0, "type": "typeA",
                     "groupby": {"project_id": "proj1"}})]
                ]
            },
        ]
        mock_retrieve.return_value = (4, loki_data_for_total)
        groupby_fields = ["type", "project_id"]
        count, result = self.client.total(
            self.begin_dt, self.end_dt, "any_metric_type",
            {"filter_key": "val"}, groupby_fields,
            None, 0, 100, False
        )
        mock_retrieve.assert_called_once_with(
            self.begin_dt, self.end_dt, {"filter_key": "val"},
            "any_metric_type", 100
        )
        self.assertEqual(count, 3)
        expected_results_map = {
            tuple(sorted({'type': 'typeA',
                          'project_id': 'proj1'}.items())):
            {'qty': 18.0, 'price': 180.0},
            tuple(sorted({'type': 'typeB',
                          'project_id': 'proj1'}.items())):
            {'qty': 5.0, 'price': 50.0},
            tuple(sorted({'type': 'typeA',
                          'project_id': 'proj2'}.items())):
            {'qty': 2.0, 'price': 20.0},
        }
        self.assertEqual(len(result), len(expected_results_map))
        for res_item in result:
            key_from_result_tuple = tuple(sorted(res_item['key'].items()))
            self.assertIn(key_from_result_tuple, expected_results_map)
            expected_values = expected_results_map[key_from_result_tuple]
            self.assertAlmostEqual(res_item['sum_qty']['value'],
                                   expected_values['qty'])
            self.assertAlmostEqual(res_item['sum_price']['value'],
                                   expected_values['price'])

    @patch.object(client.LokiClient, 'retrieve')
    def test_total_with_custom_fields_and_offset_logs_warnings(
            self, mock_retrieve, mock_log, mock_requests_arg):
        mock_retrieve.return_value = (0, [])
        custom_fields = ["field1", "field2"]
        offset = 5
        self.client.total(
            self.begin_dt, self.end_dt, None, None, None,
            custom_fields, offset, 100, False
        )
        mock_log.warning.assert_any_call(
            "'custom_fields' are not implemented yet for Loki. Therefore, "
            "the custom fields [%s] informed by the user will be ignored.",
            custom_fields
        )
        mock_log.warning.assert_any_call("offset is not supported by Loki.")

    @patch.object(client.LokiClient, '_base_query')
    def test_delete_by_query_success(self, mq, ml, mr):
        mr.post.return_value = MagicMock(status_code=204)
        test_query = '{app="cloudkitty"} | json ' \
                     '| type="compute.instance.exists"}'
        self.client.delete_by_query(test_query, self.begin_dt, self.end_dt)
        mr.post.assert_called_once_with(
            f"{self.base_url}/delete",
            params={
                "query": test_query,
                "start": int(self.begin_dt.timestamp()),
                "end": int(self.end_dt.timestamp()),
            },
            headers=self.client._headers,
            cert=self.client._cert,
            verify=self.client._verify
        )
        ml.debug.assert_has_calls([
            call("Dataframes deleted successfully.")
        ])
        mq.assert_not_called()

    @patch.object(client.LokiClient, '_base_query')
    def test_delete_by_query_failure(self, mock_base_query, mock_log,
                                     mock_requests_arg):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests_arg.post.return_value = mock_response
        test_query = '{app="cloudkitty"} | json | ' \
                     'type="compute.instance.exists"'
        self.client.delete_by_query(test_query, self.begin_dt, self.end_dt)
        expected_url = f"{self.base_url}/delete"
        expected_params = {
            "query": test_query,
            "start": int(self.begin_dt.timestamp()),
            "end": int(self.end_dt.timestamp()),
        }
        mock_requests_arg.post.assert_called_once_with(
            expected_url,
            params=expected_params,
            headers=self.client._headers,
            cert=self.client._cert,
            verify=self.client._verify
        )
        expected_error_msg = ("Failed to delete dataframes: "
                              "500 - Internal Server Error")
        mock_log.error.assert_called_once_with(expected_error_msg)
        mock_base_query.assert_not_called()

    @patch.object(client.LokiClient, 'delete_by_query')
    @patch.object(client.LokiClient, '_base_query')
    def test_delete_with_filters(self, mock_base_query, mock_delete_by_query,
                                 mock_log, mock_requests_arg):
        mock_base_query.return_value = '{app="cloudkitty", source="test"} ' \
                                       '| json'
        filters = {"project_id": "proj1", "resource_type": "instance"}
        self.client.delete(self.begin_dt, self.end_dt, filters)
        exp_query_filters = 'groupby_project_id="proj1", ' \
                            'groupby_resource_type="instance"'
        exp_query = f'{mock_base_query.return_value} | {exp_query_filters}'
        mock_delete_by_query.assert_called_once_with(
            exp_query, self.begin_dt, self.end_dt
        )
        mock_base_query.assert_called_once()

    @patch.object(client.LokiClient, 'delete_by_query')
    @patch.object(client.LokiClient, '_base_query')
    def test_delete_no_filters(self, mock_base_query, mock_delete_by_query,
                               mock_log, mock_requests_arg):
        mock_base_query.return_value = '{app="cloudkitty", source="test"} ' \
                                       '| json'
        self.client.delete(self.begin_dt, self.end_dt, None)
        mock_delete_by_query.assert_called_once_with(
            mock_base_query.return_value, self.begin_dt, self.end_dt
        )
        mock_base_query.assert_called_once()
