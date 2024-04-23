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
from collections import abc
from datetime import datetime
import itertools
from unittest import mock

from cloudkitty import storage_state
from cloudkitty import tests


class StateManagerTest(tests.TestCase):

    class QueryMock(mock.Mock):
        """Mocks an SQLalchemy query.

        ``filter()`` can be called any number of times, followed by first(),
        which will cycle over the ``output`` parameter passed to the
        constructor. The ``first_called`` attribute tracks how many times
        first() is called.
        """
        def __init__(self, output, *args, **kwargs):
            super(StateManagerTest.QueryMock, self).__init__(*args, **kwargs)
            self.first_called = 0
            if not isinstance(output, abc.Iterable):
                output = (output, )
            self.output = itertools.cycle(output)

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            self.first_called += 1
            return next(self.output)

    def setUp(self):
        super(StateManagerTest, self).setUp()
        self._state = storage_state.StateManager()
        self.conf.set_override('backend', 'fetcher1', 'fetcher')
        self.conf.set_override('collector', 'collector1', 'collect')
        self.conf.set_override('scope_key', 'scope_key', 'collect')

    def _get_query_mock(self, *args):
        output = self.QueryMock(args)
        return output, mock.Mock(return_value=output)

    @staticmethod
    def _get_r_mock(scope_key, collector, fetcher, last_processed_timestamp):
        r_mock = mock.Mock()
        r_mock.scope_key = scope_key
        r_mock.collector = collector
        r_mock.fetcher = fetcher
        r_mock.last_processed_timestamp = last_processed_timestamp
        return r_mock

    def _test_x_state_does_update_columns(self, func):
        r_mock = self._get_r_mock(None, None, None, datetime(2042, 1, 1))
        output, query_mock = self._get_query_mock(None, r_mock)
        with mock.patch('oslo_db.sqlalchemy.utils.model_query',
                        new=query_mock):
            func('fake_identifier')

        self.assertEqual(output.first_called, 2)
        self.assertEqual(r_mock.collector, 'collector1')
        self.assertEqual(r_mock.scope_key, 'scope_key')
        self.assertEqual(r_mock.fetcher, 'fetcher1')

    def test_get_last_processed_timestamp_does_update_columns(self):
        self._test_x_state_does_update_columns(
            self._state.get_last_processed_timestamp)

    def test_set_state_does_update_columns(self):
        with mock.patch('cloudkitty.db.session_for_write'):
            self._test_x_state_does_update_columns(
                lambda x: self._state.set_state(x, datetime(2042, 1, 1)))

    def _test_x_state_no_column_update(self, func):
        r_mock = self._get_r_mock(
            'scope_key', 'collector1', 'fetcher1', datetime(2042, 1, 1))
        output, query_mock = self._get_query_mock(r_mock)
        with mock.patch('oslo_db.sqlalchemy.utils.model_query',
                        new=query_mock):
            func('fake_identifier')

        self.assertEqual(output.first_called, 1)
        self.assertEqual(r_mock.collector, 'collector1')
        self.assertEqual(r_mock.scope_key, 'scope_key')
        self.assertEqual(r_mock.fetcher, 'fetcher1')

    def test_get_last_processed_timestamp_no_column_update(self):
        self._test_x_state_no_column_update(
            self._state.get_last_processed_timestamp)

    def test_set_state_no_column_update(self):
        with mock.patch('cloudkitty.db.session_for_write'):
            self._test_x_state_no_column_update(
                lambda x: self._state.set_state(x, datetime(2042, 1, 1)))

    def test_set_state_does_not_duplicate_entries(self):
        state = datetime(2042, 1, 1)
        _, query_mock = self._get_query_mock(
            self._get_r_mock('a', 'b', 'c', state))
        with mock.patch(
                'oslo_db.sqlalchemy.utils.model_query',
                new=query_mock), mock.patch(
                    'cloudkitty.db.session_for_write') as sm:
            sm.return_value.__enter__.return_value = session_mock = \
                mock.MagicMock()
            self._state.set_state('fake_identifier', state)
            session_mock.commit.assert_not_called()
            session_mock.add.assert_not_called()

    def test_set_state_does_update_state(self):
        r_mock = self._get_r_mock('a', 'b', 'c', datetime(2000, 1, 1))
        _, query_mock = self._get_query_mock(r_mock)
        new_state = datetime(2042, 1, 1)
        with mock.patch(
                'oslo_db.sqlalchemy.utils.model_query',
                new=query_mock), mock.patch(
                    'cloudkitty.db.session_for_write') as sm:
            sm.return_value.__enter__.return_value = session_mock = \
                mock.MagicMock()
            self.assertNotEqual(r_mock.state, new_state)
            self._state.set_state('fake_identifier', new_state)
            self.assertEqual(r_mock.last_processed_timestamp, new_state)
            session_mock.commit.assert_called_once()
            session_mock.add.assert_not_called()
