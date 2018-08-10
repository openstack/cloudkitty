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
import copy
from datetime import datetime
import decimal
import fixtures
import testtools

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_utils import uuidutils

from cloudkitty import storage
from cloudkitty.tests import samples
from cloudkitty import utils as ck_utils


CONF = None


def _init_conf():
    global CONF
    if not CONF:
        CONF = cfg.CONF
        CONF(args=[], project='cloudkitty',
             validate_default_values=True,
             default_config_files=['/etc/cloudkitty/cloudkitty.conf'])


def get_storage_data(min_length=10,
                     nb_projects=2,
                     project_ids=None,
                     start=datetime(2018, 1, 1),
                     end=datetime(2018, 1, 1, 1)):
    if isinstance(start, datetime):
        start = ck_utils.dt2ts(start)
    if isinstance(end, datetime):
        end = ck_utils.dt2ts(end)

    if not project_ids:
        project_ids = [uuidutils.generate_uuid() for i in range(nb_projects)]
    elif not isinstance(project_ids, list):
        project_ids = [project_ids]

    usage = {}
    for metric_name, sample in samples.V2_STORAGE_SAMPLE.items():
        dataframes = []
        for project_id in project_ids:
            data = [copy.deepcopy(sample)
                    # for i in range(min_length + random.randint(1, 10))]
                    for i in range(1)]
            for elem in data:
                elem['groupby']['id'] = uuidutils.generate_uuid()
                elem['groupby']['project_id'] = project_id
            dataframes += data
        usage[metric_name] = dataframes

    return {
        'usage': usage,
        'period': {
            'begin': start,
            'end': end
        }
    }


class BaseFunctionalStorageTest(testtools.TestCase):

    # Name of the storage backend to test
    storage_backend = None
    storage_version = 0

    @classmethod
    def setUpClass(cls):
        _init_conf()
        cls._conf_fixture = config_fixture.Config(conf=CONF)
        cls._conf_fixture.set_config_files(
            ['/etc.cloudkitty/cloudkitty.conf'])
        cls.conf = cls._conf_fixture.conf
        cls.conf.set_override('version', cls.storage_version, 'storage')
        cls.conf.set_override('backend', cls.storage_backend, 'storage')
        cls.storage = storage.get_storage()
        cls.storage.init()
        cls.project_ids, cls.data = cls.gen_data_separate_projects(3)
        for i, project_data in enumerate(cls.data):
            cls.storage.push(project_data, cls.project_ids[i])

        # Appending data for the second tenant
        data_next_period = copy.deepcopy(cls.data[0])
        data_next_period['period']['begin'] += 3600
        data_next_period['period']['end'] += 3600
        cls.storage.push(data_next_period, cls.project_ids[0])
        cls.project_ids.append(cls.project_ids[0])
        cls.data.append(data_next_period)

        cls.wait_for_backend()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_backend()
        # cls._conf_fixture.cleanUp()
        # pass

    def setUp(self):
        super(BaseFunctionalStorageTest, self).setUp()
        self.useFixture(fixtures.FakeLogger())
        self.useFixture(self._conf_fixture)

    def cleanUp(self):
        super(BaseFunctionalStorageTest, self).cleanUp()

    @classmethod
    def wait_for_backend(cls):
        """Function waiting for the storage backend to be ready.

        Ex: wait for gnocchi to have processed all metrics
        """

    @classmethod
    def cleanup_backend(cls):
        """Function deleting everything from the storage backend"""

    @staticmethod
    def gen_data_separate_projects(nb_projects):
        project_ids = [uuidutils.generate_uuid() for i in range(nb_projects)]
        data = [get_storage_data(
            project_ids=project_ids[i], nb_projects=1)
            for i in range(nb_projects)]
        return project_ids, data

    def test_get_retention(self):
        retention = self.storage.get_retention().days * 24
        self.assertEqual(retention, self.conf.storage.retention_period)

    @staticmethod
    def _validate_filters(comp, filters=None, group_filters=None):
        if group_filters:
            for k, v in group_filters.items():
                if comp['groupby'].get(k) != v:
                    return False
        if filters:
            for k, v in filters.items():
                if comp['metadata'].get(k) != v:
                    return False
        return True

    def _get_expected_total(self, begin=None, end=None,
                            filters=None, group_filters=None):
        total = decimal.Decimal(0)
        for dataframes in self.data:
            if (ck_utils.ts2dt(dataframes['period']['begin']) >= end
               or ck_utils.ts2dt(dataframes['period']['end']) <= begin):
                continue
            for df in dataframes['usage'].values():
                for elem in df:
                    if self._validate_filters(elem, filters, group_filters):
                        total += elem['rating']['price']
        return total

    def _compare_totals(self, expected_total, total):
        self.assertEqual(len(total), len(expected_total))
        for i in range(len(total)):
            self.assertEqual(
                round(expected_total[i], 5),
                round(decimal.Decimal(total[i]['rate']), 5),
            )

    def test_get_total_all_projects_on_time_window_with_data_no_grouping(self):
        expected_total = self._get_expected_total(begin=datetime(2018, 1, 1),
                                                  end=datetime(2018, 1, 1, 1))
        total = self.storage.total(begin=datetime(2018, 1, 1),
                                   end=datetime(2018, 1, 1, 1))
        self.assertEqual(len(total), 1)
        self.assertEqual(
            round(expected_total, 5),
            round(decimal.Decimal(total[0]['rate']), 5),
        )

    def test_get_total_one_project_on_time_window_with_data_no_grouping(self):
        group_filters = {'project_id': self.project_ids[0]}
        expected_total = self._get_expected_total(
            begin=datetime(2018, 1, 1), end=datetime(2018, 1, 1, 1),
            group_filters=group_filters)
        total = self.storage.total(begin=datetime(2018, 1, 1),
                                   end=datetime(2018, 1, 1, 1),
                                   group_filters=group_filters)
        self.assertEqual(len(total), 1)
        self.assertEqual(
            round(expected_total, 5),
            round(decimal.Decimal(total[0]['rate']), 5),
        )

    def test_get_total_all_projects_window_with_data_group_by_project_id(self):
        expected_total = []
        for project_id in sorted(self.project_ids[:-1]):
            group_filters = {'project_id': project_id}
            expected_total.append(self._get_expected_total(
                begin=datetime(2018, 1, 1), end=datetime(2018, 1, 1, 1),
                group_filters=group_filters))

        total = self.storage.total(begin=datetime(2018, 1, 1),
                                   end=datetime(2018, 1, 1, 1),
                                   groupby=['project_id'])
        total = sorted(total, key=lambda k: k['project_id'])

        self._compare_totals(expected_total, total)

    def test_get_total_one_project_window_with_data_group_by_resource_id(self):
        expected_total = []
        for df in self.data[0]['usage'].values():
            expected_total += copy.deepcopy(df)
        for df in self.data[-1]['usage'].values():
            for df_elem in df:
                for elem in expected_total:
                    if elem['groupby'] == df_elem['groupby']:
                        elem['rating']['price'] += df_elem['rating']['price']
        expected_total = sorted(
            expected_total, key=lambda k: k['groupby']['id'])
        expected_total = [i['rating']['price'] for i in expected_total]

        total = self.storage.total(
            begin=datetime(2018, 1, 1), end=datetime(2018, 1, 1, 2),
            group_filters={'project_id': self.project_ids[0]},
            groupby=['id'])
        total = sorted(total, key=lambda k: k['id'])

        self._compare_totals(expected_total, total)

    def test_get_total_all_projects_group_by_resource_id_project_id(self):
        expected_total = []
        for data in self.data[:-1]:
            for df in data['usage'].values():
                expected_total += copy.deepcopy(df)
        for df in self.data[-1]['usage'].values():
            for elem in df:
                for total_elem in expected_total:
                    if total_elem['groupby'] == elem['groupby']:
                        total_elem['rating']['price'] \
                            += elem['rating']['price']
        expected_total = sorted(
            expected_total, key=lambda k: k['groupby']['id'])
        expected_total = [i['rating']['price'] for i in expected_total]

        total = self.storage.total(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            groupby=['id', 'project_id'])
        total = sorted(total, key=lambda k: k['id'])

        self._compare_totals(expected_total, total)

    def test_get_total_all_projects_group_by_resource_type(self):
        expected_total = {}
        for data in self.data:
            for res_type, df in data['usage'].items():
                if expected_total.get(res_type):
                    expected_total[res_type] += sum(
                        elem['rating']['price'] for elem in df)
                else:
                    expected_total[res_type] = sum(
                        elem['rating']['price'] for elem in df)
        expected_total = [
            expected_total[key] for key in sorted(expected_total.keys())]
        total = self.storage.total(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            groupby=['type'])
        total = sorted(total, key=lambda k: k['type'])

        self._compare_totals(expected_total, total)

    def test_get_total_one_project_group_by_resource_type(self):
        expected_total = {}
        for res_type, df in self.data[0]['usage'].items():
            expected_total[res_type] = sum(
                elem['rating']['price'] for elem in df)
        expected_total = [
            expected_total[key] for key in sorted(expected_total.keys())]

        group_filters = {'project_id': self.project_ids[0]}
        total = self.storage.total(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 1, 1, 1),
            group_filters=group_filters,
            groupby=['type'])
        total = sorted(total, key=lambda k: k['type'])

        self._compare_totals(expected_total, total)

    def test_get_total_no_data_period(self):
        total = self.storage.total(
            begin=datetime(2018, 2, 1), end=datetime(2018, 2, 1, 1))
        self.assertEqual(0, len(total))

    def test_retrieve_all_projects_with_data(self):
        expected_length = sum(
            len(data['usage'].values()) for data in self.data)

        frames = self.storage.retrieve(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            limit=1000)

        self.assertEqual(expected_length, frames['total'])
        self.assertEqual(2, len(frames['dataframes']))

    def test_retrieve_one_project_with_data(self):
        expected_length = len(self.data[0]['usage'].values()) \
            + len(self.data[-1]['usage'].values())

        group_filters = {'project_id': self.project_ids[0]}
        frames = self.storage.retrieve(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            group_filters=group_filters,
            limit=1000)

        self.assertEqual(expected_length, frames['total'])
        self.assertEqual(2, len(frames['dataframes']))
        for metric_type in self.data[0]['usage'].keys():
            self.assertEqual(
                len(frames['dataframes'][0]['usage'][metric_type]),
                len(self.data[0]['usage'][metric_type]))
        for metric_type in self.data[-1]['usage'].keys():
            self.assertEqual(
                len(frames['dataframes'][1]['usage'][metric_type]),
                len(self.data[-1]['usage'][metric_type]))

    def test_retrieve_pagination_one_project(self):
        expected_length = len(self.data[0]['usage'].values()) \
            + len(self.data[-1]['usage'].values())

        group_filters = {'project_id': self.project_ids[0]}
        first_frames = self.storage.retrieve(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            group_filters=group_filters,
            limit=5)
        last_frames = self.storage.retrieve(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            group_filters=group_filters,
            offset=5,
            limit=1000)
        all_frames = self.storage.retrieve(
            begin=datetime(2018, 1, 1),
            end=datetime(2018, 2, 1),
            group_filters=group_filters,
            paginate=False)

        self.assertEqual(expected_length, first_frames['total'])
        self.assertEqual(expected_length, last_frames['total'])

        real_length = 0
        paginated_measures = []

        for frame in first_frames['dataframes'] + last_frames['dataframes']:
            for measures in frame['usage'].values():
                real_length += len(measures)
                paginated_measures += measures
        paginated_measures = sorted(
            paginated_measures, key=lambda x: x['groupby']['id'])

        all_measures = []
        for frame in all_frames['dataframes']:
            for measures in frame['usage'].values():
                all_measures += measures
        all_measures = sorted(
            all_measures, key=lambda x: x['groupby']['id'])

        self.assertEqual(expected_length, real_length)
        self.assertEqual(paginated_measures, all_measures)
