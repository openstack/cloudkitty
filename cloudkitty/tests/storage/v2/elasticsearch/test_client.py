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
import collections
import datetime
import unittest
from unittest import mock

from dateutil import tz

from cloudkitty import dataframe
from cloudkitty.storage.v2.elasticsearch import client
from cloudkitty.storage.v2.elasticsearch import exceptions


class TestElasticsearchClient(unittest.TestCase):

    def setUp(self):
        super(TestElasticsearchClient, self).setUp()
        self.client = client.ElasticsearchClient(
            'http://elasticsearch:9200',
            'index_name',
            'test_mapping',
            autocommit=False)

    def test_build_must_no_params(self):
        self.assertEqual(self.client._build_must(None, None, None, None), [])

    def test_build_must_with_start_end(self):
        start = datetime.datetime(2019, 8, 30, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 8, 31, tzinfo=tz.tzutc())
        self.assertEqual(
            self.client._build_must(start, end, None, None),
            [{'range': {'start': {'gte': '2019-08-30T00:00:00+00:00'}}},
             {'range': {'end': {'lte': '2019-08-31T00:00:00+00:00'}}}],
        )

    def test_build_must_with_filters(self):
        filters = {'one': '1', 'two': '2', 'type': 'awesome'}
        self.assertEqual(
            self.client._build_must(None, None, None, filters),
            [{'term': {'type': 'awesome'}}],
        )

    def test_build_must_with_metric_types(self):
        types = ['awesome', 'amazing']
        self.assertEqual(
            self.client._build_must(None, None, types, None),
            [{'terms': {'type': ['awesome', 'amazing']}}],
        )

    def test_build_should_no_filters(self):
        self.assertEqual(
            self.client._build_should(None),
            [],
        )

    def test_build_should_with_filters(self):
        filters = collections.OrderedDict([
            ('one', '1'), ('two', '2'), ('type', 'awesome')])
        self.assertEqual(
            self.client._build_should(filters),
            [
                {'term': {'groupby.one': '1'}},
                {'term': {'metadata.one': '1'}},
                {'term': {'groupby.two': '2'}},
                {'term': {'metadata.two': '2'}},
            ],
        )

    def test_build_composite_no_groupby(self):
        self.assertEqual(self.client._build_composite(None), [])

    def test_build_composite(self):
        self.assertEqual(
            self.client._build_composite(['one', 'type', 'two']),
            {'sources': [
                {'one': {'terms': {'field': 'groupby.one'}}},
                {'type': {'terms': {'field': 'type'}}},
                {'two': {'terms': {'field': 'groupby.two'}}},
            ]},
        )

    def test_build_query_no_args(self):
        self.assertEqual(self.client._build_query(None, None, None), {})

    def test_build_query(self):
        must = [{'range': {'start': {'gte': '2019-08-30T00:00:00+00:00'}}},
                {'range': {'start': {'lt': '2019-08-31T00:00:00+00:00'}}}]
        should = [
            {'term': {'groupby.one': '1'}},
            {'term': {'metadata.one': '1'}},
            {'term': {'groupby.two': '2'}},
            {'term': {'metadata.two': '2'}},
        ]
        composite = {'sources': [
            {'one': {'terms': {'field': 'groupby.one'}}},
            {'type': {'terms': {'field': 'type'}}},
            {'two': {'terms': {'field': 'groupby.two'}}},
        ]}
        expected = {
            'query': {
                'bool': {
                    'must': must,
                    'should': should,
                    'minimum_should_match': 2,
                },
            },
            'aggs': {
                'sum_and_price': {
                    'composite': composite,
                    'aggregations': {
                        "sum_price": {"sum": {"field": "price"}},
                        "sum_qty": {"sum": {"field": "qty"}},
                    },
                },
            },
        }
        self.assertEqual(
            self.client._build_query(must, should, composite), expected)

    def test_log_query_no_hits(self):
        url = '/endpoint'
        body = {'1': 'one'}
        response = {'took': 42}
        expected = """Query on /endpoint with body "{'1': 'one'}" took 42ms"""
        with mock.patch.object(client.LOG, 'debug') as debug_mock:
            self.client._log_query(url, body, response)
            debug_mock.assert_called_once_with(expected)

    def test_log_query_with_hits(self):
        url = '/endpoint'
        body = {'1': 'one'}
        response = {'took': 42, 'hits': {'total': 1337}}
        expected = """Query on /endpoint with body "{'1': 'one'}" took 42ms"""
        expected += " for 1337 hits"
        with mock.patch.object(client.LOG, 'debug') as debug_mock:
            self.client._log_query(url, body, response)
            debug_mock.assert_called_once_with(expected)

    def test_req_valid_status_code_no_deserialize(self):
        resp_mock = mock.MagicMock()
        resp_mock.status_code = 200
        method_mock = mock.MagicMock()
        method_mock.return_value = resp_mock
        req_resp = self.client._req(
            method_mock, None, None, None, deserialize=False)
        method_mock.assert_called_once_with(None, data=None, params=None)
        self.assertEqual(req_resp, resp_mock)

    def test_req_valid_status_code_deserialize(self):
        resp_mock = mock.MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = 'output'
        method_mock = mock.MagicMock()
        method_mock.return_value = resp_mock
        with mock.patch.object(self.client, '_log_query') as log_mock:
            req_resp = self.client._req(
                method_mock, None, None, None, deserialize=True)
            method_mock.assert_called_once_with(None, data=None, params=None)
            self.assertEqual(req_resp, 'output')
            log_mock.assert_called_once_with(None, None, 'output')

    def test_req_invalid_status_code(self):
        resp_mock = mock.MagicMock()
        resp_mock.status_code = 400
        method_mock = mock.MagicMock()
        method_mock.return_value = resp_mock
        self.assertRaises(exceptions.InvalidStatusCode,
                          self.client._req,
                          method_mock, None, None, None)

    def test_put_mapping(self):
        mapping = {'a': 'b'}
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.put_mapping(mapping)
            rmock.assert_called_once_with(
                self.client._sess.put,
                'http://elasticsearch:9200/index_name/_mapping/test_mapping',
                '{"a": "b"}', {'include_type_name': 'true'}, deserialize=False)

    def test_get_index(self):
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.get_index()
            rmock.assert_called_once_with(
                self.client._sess.get,
                'http://elasticsearch:9200/index_name',
                None, None, deserialize=False)

    def test_search_without_scroll(self):
        mapping = {'a': 'b'}
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.search(mapping, scroll=False)
            rmock.assert_called_once_with(
                self.client._sess.get,
                'http://elasticsearch:9200/index_name/_search',
                '{"a": "b"}', None)

    def test_search_with_scroll(self):
        mapping = {'a': 'b'}
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.search(mapping, scroll=True)
            rmock.assert_called_once_with(
                self.client._sess.get,
                'http://elasticsearch:9200/index_name/_search',
                '{"a": "b"}', {'scroll': '60s'})

    def test_scroll(self):
        body = {'a': 'b'}
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.scroll(body)
            rmock.assert_called_once_with(
                self.client._sess.get,
                'http://elasticsearch:9200/_search/scroll',
                '{"a": "b"}', None)

    def test_close_scroll(self):
        body = {'a': 'b'}
        with mock.patch.object(self.client, '_req') as rmock:
            self.client.close_scroll(body)
            rmock.assert_called_once_with(
                self.client._sess.delete,
                'http://elasticsearch:9200/_search/scroll',
                '{"a": "b"}', None, deserialize=False)

    def test_close_scrolls(self):
        with mock.patch.object(self.client, 'close_scroll') as func_mock:
            with mock.patch.object(self.client, '_scroll_ids',
                                   new=['a', 'b', 'c']):
                self.client.close_scrolls()
                func_mock.assert_called_once_with(
                    {'scroll_id': ['a', 'b', 'c']})
                self.assertSetEqual(set(), self.client._scroll_ids)

    def test_bulk_with_instruction(self):
        instruction = {'instruction': {}}
        terms = ('one', 'two', 'three')
        expected_data = ''.join([
            '{"instruction": {}}\n'
            '"one"\n'
            '{"instruction": {}}\n'
            '"two"\n'
            '{"instruction": {}}\n'
            '"three"\n',
        ])

        with mock.patch.object(self.client, '_req') as rmock:
            self.client.bulk_with_instruction(instruction, terms)
            rmock.assert_called_once_with(
                self.client._sess.post,
                'http://elasticsearch:9200/index_name/test_mapping/_bulk',
                expected_data, None, deserialize=False)

    def test_bulk_index(self):
        terms = ('one', 'two', 'three')
        with mock.patch.object(self.client, 'bulk_with_instruction') as fmock:
            self.client.bulk_index(terms)
            fmock.assert_called_once_with({'index': {}}, terms)

    def test_commit(self):
        docs = ['one', 'two', 'three', 'four', 'five', 'six', 'seven']
        size = 3
        with mock.patch.object(self.client, 'bulk_index') as bulk_mock:
            with mock.patch.object(self.client, '_docs', new=docs):
                with mock.patch.object(self.client, '_chunk_size', new=size):
                    self.client.commit()
                    bulk_mock.assert_has_calls([
                        mock.call(['one', 'two', 'three']),
                        mock.call(['four', 'five', 'six']),
                        mock.call(['seven']),
                    ])

    def test_add_point_no_autocommit(self):
        point = dataframe.DataPoint(
            'unit', '0.42', '0.1337', {}, {})
        start = datetime.datetime(2019, 1, 1)
        end = datetime.datetime(2019, 1, 1, 1)
        with mock.patch.object(self.client, 'commit') as func_mock:
            with mock.patch.object(self.client, '_autocommit', new=False):
                with mock.patch.object(self.client, '_chunk_size', new=3):
                    self.client._docs = []
                    for _ in range(5):
                        self.client.add_point(
                            point, 'awesome_type', start, end)

                    func_mock.assert_not_called()
                    self.assertEqual(self.client._docs, [{
                        'start': start,
                        'end': end,
                        'type': 'awesome_type',
                        'unit': point.unit,
                        'description': point.description,
                        'qty': point.qty,
                        'price': point.price,
                        'groupby': point.groupby,
                        'metadata': point.metadata,
                    } for _ in range(5)])

        self.client._docs = []

    def test_add_point_with_autocommit(self):
        point = dataframe.DataPoint(
            'unit', '0.42', '0.1337', {}, {})
        start = datetime.datetime(2019, 1, 1)
        end = datetime.datetime(2019, 1, 1, 1)

        commit_calls = {'count': 0}

        def commit():
            # We can't re-assign nonlocal variables in python2
            commit_calls['count'] += 1
            self.client._docs = []

        with mock.patch.object(self.client, 'commit', new=commit):
            with mock.patch.object(self.client, '_autocommit', new=True):
                with mock.patch.object(self.client, '_chunk_size', new=3):
                    self.client._docs = []
                    for i in range(5):
                        self.client.add_point(
                            point, 'awesome_type', start, end)

                    self.assertEqual(commit_calls['count'], 1)
                    self.assertEqual(self.client._docs, [{
                        'start': start,
                        'end': end,
                        'type': 'awesome_type',
                        'unit': point.unit,
                        'description': point.description,
                        'qty': point.qty,
                        'price': point.price,
                        'groupby': point.groupby,
                        'metadata': point.metadata,
                    } for _ in range(2)])

        # cleanup
        self.client._docs = []

    def test_delete_by_query_with_must(self):
        with mock.patch.object(self.client, '_req') as rmock:
            with mock.patch.object(self.client, '_build_must') as func_mock:
                func_mock.return_value = {'a': 'b'}
                self.client.delete_by_query()
                rmock.assert_called_once_with(
                    self.client._sess.post,
                    'http://elasticsearch:9200/index_name/_delete_by_query',
                    '{"query": {"bool": {"must": {"a": "b"}}}}', None)

    def test_delete_by_query_no_must(self):
        with mock.patch.object(self.client, '_req') as rmock:
            with mock.patch.object(self.client, '_build_must') as func_mock:
                func_mock.return_value = {}
                self.client.delete_by_query()
                rmock.assert_called_once_with(
                    self.client._sess.post,
                    'http://elasticsearch:9200/index_name/_delete_by_query',
                    None, None)

    def test_retrieve_no_pagination(self):
        search_resp = {
            '_scroll_id': '000',
            'hits': {'hits': ['one', 'two', 'three'], 'total': 12},
        }
        scroll_resps = [{
            '_scroll_id': str(i + 1) * 3,
            'hits': {'hits': ['one', 'two', 'three']},
        } for i in range(3)]
        scroll_resps.append({'_scroll_id': '444', 'hits': {'hits': []}})

        self.client._scroll_ids = set()

        with mock.patch.object(self.client, 'search') as search_mock:
            with mock.patch.object(self.client, 'scroll') as scroll_mock:
                with mock.patch.object(self.client, 'close_scrolls') as close:
                    search_mock.return_value = search_resp
                    scroll_mock.side_effect = scroll_resps

                    total, resp = self.client.retrieve(
                        None, None, None, None, paginate=False)
                    search_mock.assert_called_once()
                    scroll_mock.assert_has_calls([
                        mock.call({
                            'scroll_id': str(i) * 3,
                            'scroll': '60s',
                        }) for i in range(4)
                    ])
                    self.assertEqual(total, 12)
                    self.assertEqual(resp, ['one', 'two', 'three'] * 4)
                    self.assertSetEqual(self.client._scroll_ids,
                                        set(str(i) * 3 for i in range(5)))
                    close.assert_called_once()

        self.client._scroll_ids = set()

    def test_retrieve_with_pagination(self):
        search_resp = {
            '_scroll_id': '000',
            'hits': {'hits': ['one', 'two', 'three'], 'total': 12},
        }
        scroll_resps = [{
            '_scroll_id': str(i + 1) * 3,
            'hits': {'hits': ['one', 'two', 'three']},
        } for i in range(3)]
        scroll_resps.append({'_scroll_id': '444', 'hits': {'hits': []}})

        self.client._scroll_ids = set()

        with mock.patch.object(self.client, 'search') as search_mock:
            with mock.patch.object(self.client, 'scroll') as scroll_mock:
                with mock.patch.object(self.client, 'close_scrolls') as close:
                    search_mock.return_value = search_resp
                    scroll_mock.side_effect = scroll_resps

                    total, resp = self.client.retrieve(
                        None, None, None, None,
                        offset=2, limit=4, paginate=True)
                    search_mock.assert_called_once()
                    scroll_mock.assert_called_once_with({
                        'scroll_id': '000',
                        'scroll': '60s',
                    })
                    self.assertEqual(total, 12)
                    self.assertEqual(resp, ['three', 'one', 'two', 'three'])
                    self.assertSetEqual(self.client._scroll_ids,
                                        set(str(i) * 3 for i in range(2)))
                    close.assert_called_once()

        self.client._scroll_ids = set()

    def _do_test_total(self, groupby, paginate):
        with mock.patch.object(self.client, 'search') as search_mock:
            if groupby:
                search_resps = [{
                    'aggregations': {
                        'sum_and_price': {
                            'buckets': ['one', 'two', 'three'],
                            'after_key': str(i),
                        }
                    }
                } for i in range(3)]
                last_resp_aggs = search_resps[2]['aggregations']
                last_resp_aggs['sum_and_price'].pop('after_key')
                last_resp_aggs['sum_and_price']['buckets'] = []
                search_mock.side_effect = search_resps
            else:
                search_mock.return_value = {
                    'aggregations': ['one', 'two', 'three'],
                }
            resp = self.client.total(None, None, None, None, groupby,
                                     offset=2, limit=4, paginate=paginate)
            if not groupby:
                search_mock.assert_called_once()

        return resp

    def test_total_no_groupby_no_pagination(self):
        total, aggs = self._do_test_total(None, False)
        self.assertEqual(total, 1)
        self.assertEqual(aggs, [['one', 'two', 'three']])

    def test_total_no_groupby_with_pagination(self):
        total, aggs = self._do_test_total(None, True)
        self.assertEqual(total, 1)
        self.assertEqual(aggs, [['one', 'two', 'three']])

    def test_total_with_groupby_no_pagination(self):
        total, aggs = self._do_test_total(['x'], False)
        self.assertEqual(total, 6)
        self.assertEqual(aggs, ['one', 'two', 'three'] * 2)

    def test_total_with_groupby_with_pagination(self):
        total, aggs = self._do_test_total(['x'], True)
        self.assertEqual(total, 6)
        self.assertEqual(aggs, ['three', 'one', 'two', 'three'])
