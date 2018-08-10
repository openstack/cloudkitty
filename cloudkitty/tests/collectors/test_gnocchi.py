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
#
import testtools

from cloudkitty.collector import gnocchi
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty.tests.utils import is_functional_test


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class GnocchiCollectorTest(tests.TestCase):
    def setUp(self):
        super(GnocchiCollectorTest, self).setUp()
        self._tenant_id = samples.TENANT
        self.collector = gnocchi.GnocchiCollector

    # Filter generation
    def test_generate_one_field_filter(self):
        actual = self.collector.gen_filter(value1=2)
        expected = {
            '=': {
                'value1': 2
            }}
        self.assertEqual(expected, actual)

    def test_generate_two_fields_filter(self):
        actual = self.collector.gen_filter(value1=2, value2=3)
        expected = {'and': [{
            '=': {
                'value1': 2
            }}, {
            '=': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_generate_two_fields_filter_different_operations(self):
        actual = self.collector.gen_filter(
            cop='>=',
            lop='or',
            value1=2,
            value2=3)
        expected = {'or': [{
            '>=': {
                'value1': 2
            }}, {
            '>=': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_generate_two_filters_and_add_logical(self):
        filter1 = self.collector.gen_filter(value1=2)
        filter2 = self.collector.gen_filter(cop='>', value2=3)
        actual = self.collector.extend_filter(filter1, filter2, lop='or')
        expected = {'or': [{
            '=': {
                'value1': 2
            }}, {
            '>': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_noop_on_single_filter(self):
        filter1 = self.collector.gen_filter(value1=2)
        actual = self.collector.extend_filter(filter1, lop='or')
        self.assertEqual(filter1, actual)

    def test_try_extend_empty_filter(self):
        actual = self.collector.extend_filter()
        self.assertEqual({}, actual)
        actual = self.collector.extend_filter(actual, actual)
        self.assertEqual({}, actual)

    def test_try_extend_filter_with_none(self):
        filter1 = self.collector.gen_filter(value1=2)
        actual = self.collector.extend_filter(filter1, None)
        self.assertEqual(filter1, actual)

    def test_generate_two_logical_ops(self):
        filter1 = self.collector.gen_filter(value1=2, value2=3)
        filter2 = self.collector.gen_filter(cop='<=', value3=1)
        actual = self.collector.extend_filter(filter1, filter2, lop='or')
        expected = {'or': [{
            'and': [{
                '=': {
                    'value1': 2
                }}, {
                '=': {
                    'value2': 3
                }}]}, {
            '<=': {
                'value3': 1
            }}]}
        self.assertEqual(expected, actual)

    def test_gen_filter_parameters(self):
        actual = self.collector.gen_filter(
            cop='>',
            lop='or',
            value1=2,
            value2=3)
        expected = {'or': [{
            '>': {
                'value1': 2
            }}, {
            '>': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_extend_filter_parameters(self):
        actual = self.collector.extend_filter(
            ['dummy1'],
            ['dummy2'],
            lop='or')
        expected = {'or': ['dummy1', 'dummy2']}
        self.assertEqual(expected, actual)
