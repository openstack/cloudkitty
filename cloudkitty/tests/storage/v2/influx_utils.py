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
import copy
import functools

from influxdb import resultset

from cloudkitty.storage.v2.influx import _sanitized_groupby
from cloudkitty.storage.v2.influx import InfluxClient


class FakeInfluxClient(InfluxClient):

    total_sample = {
        "statement_id": 0,
        "series": []
    }

    total_series_sample = {
        "name": "dataframes",
        "tags": {},
        "columns": ["time", "qty", "price"],
        "values": [],
    }

    def __init__(self, **kwargs):
        super(FakeInfluxClient, self).__init__(autocommit=False)

    def commit(self):
        pass

    @staticmethod
    def __filter_func(types, filters, begin, end, elem):
        if elem['time'] < begin or elem['time'] >= end:
            return False
        if types and elem['tags']['type'] not in types:
            return False
        if filters is None:
            return True
        for key in filters.keys():
            if key not in elem['tags'].keys():
                return False
            if elem['tags'][key] != filters[key]:
                return False
        return True

    def __get_target_serie(self, point, series, groupby):
        target_serie = None
        for serie in series:
            if not groupby:
                target_serie = serie
                break
            valid = True
            for tag in serie['tags'].keys():
                if tag == 'time':
                    if point['time'].isoformat() != serie['values'][0][0]:
                        valid = False
                        break
                    else:
                        continue
                if tag not in point['tags'].keys() or \
                   point['tags'][tag] != serie['tags'][tag]:
                    valid = False
                    break
            if valid:
                target_serie = serie
                break

        if target_serie is None:
            target_serie = copy.deepcopy(self.total_series_sample)
            if groupby:
                target_serie['tags'] = {k: point['tags'][k] for k in
                                        _sanitized_groupby(groupby)}
            else:
                target_serie['tags'] = {}
            target_serie['values'] = [[point['time'].isoformat(), 0, 0]]
            series.append(target_serie)
        return target_serie

    def get_total(self, types, begin, end, custom_fields, groupby=None,
                  filters=None, limit=None):
        total = copy.deepcopy(self.total_sample)
        series = []

        filter_func = functools.partial(
            self.__filter_func, types, filters, begin, end)
        points = filter(filter_func, self._points)

        for point in points:
            target_serie = self.__get_target_serie(point, series, groupby)
            target_serie['values'][0][1] += point['fields']['qty']
            target_serie['values'][0][2] += point['fields']['price']
        total['series'] = series

        return resultset.ResultSet(total)

    def retrieve(self,
                 types,
                 filters,
                 begin, end,
                 offset=0, limit=1000, paginate=True):
        output = copy.deepcopy(self.total_sample)

        filter_func = functools.partial(
            self.__filter_func, types, filters, begin, end)
        points = list(filter(filter_func, self._points))

        columns = set()
        for point in points:
            columns.update(point['tags'].keys())
            columns.update(point['fields'].keys())
        columns.add('time')

        series = {
            'name': 'dataframes',
            'columns': list(columns),
        }
        values = []

        def __get_tag_or_field(point, key):
            if key == 'time':
                return point['time'].isoformat()
            return point['tags'].get(key) or point['fields'].get(key)

        for point in points:
            values.append([__get_tag_or_field(point, key)
                           for key in series['columns']])

        series['values'] = values
        output['series'] = [series]

        return len(list(points)), resultset.ResultSet(output)

    def delete(self, begin, end, filters):

        def __filter_func(elem):

            def __time(elem):
                return ((begin and begin > elem['time'])
                        or (end and end <= elem['time']))

            def __filt(elem):
                return all(
                    (elem['tags'].get(k, None) == v
                     or elem['fields'].get(k, None) == v)
                    for k, v in filters.items())

            return __time(elem) and __filt(elem)

        self._points = list(filter(__filter_func, self._points))

    def retention_policy_exists(self, database, policy):
        return True
