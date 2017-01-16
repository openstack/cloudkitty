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
# @author: Stéphane Albert
#
import csv
import json

from oslo_config import cfg

from cloudkitty import collector

fake_collector_opts = [
    cfg.StrOpt('file',
               default='/var/lib/cloudkitty/input.csv',
               help='Collector input file.')]

cfg.CONF.register_opts(fake_collector_opts, 'fake_collector')


class CSVCollector(collector.BaseCollector):
    collector_name = 'csvcollector'
    dependencies = ('CloudKittyFormatTransformer', )

    def __init__(self, transformers, **kwargs):
        super(CSVCollector, self).__init__(transformers, **kwargs)

        self.t_cloudkitty = self.transformers['CloudKittyFormatTransformer']
        self._file = None
        self._csv = None

    def _open_csv(self):
        filename = cfg.CONF.fake_collector.file
        csvfile = open(filename, 'rb')
        reader = csv.DictReader(csvfile)
        self._file = csvfile
        self._csv = reader

    @classmethod
    def get_metadata(cls, resource_name, transformers):
        res = super(CSVCollector, cls).get_metadata(resource_name,
                                                    transformers)
        try:
            filename = cfg.CONF.fake_collector.file
            csvfile = open(filename, 'rb')
            reader = csv.DictReader(csvfile)
            entry = None
            for row in reader:
                if row['type'] == resource_name:
                    entry = row
                    break
            res['metadata'] = json.loads(entry['desc']).keys() if entry else {}
        except IOError:
            pass
        return res

    def filter_rows(self,
                    start,
                    end=None,
                    project_id=None,
                    res_type=None):
        rows = []
        for row in self._csv:
            if int(row['begin']) == start:
                if res_type:
                    if row['type'] == res_type:
                        rows.append(row)
                else:
                    rows.append(row)
        return rows

    def _get_data(self,
                  res_type,
                  start,
                  end=None,
                  project_id=None,
                  q_filter=None):
        self._open_csv()
        rows = self.filter_rows(start, end, project_id, res_type=res_type)
        data = []
        for row in rows:
            data.append({
                'desc': json.loads(row['desc']),
                'vol': json.loads(row['vol'])})
        if not data:
            raise collector.NoDataCollected(self.collector_name, res_type)
        return self.t_cloudkitty.format_service(res_type, data)

    def get_compute(self,
                    start,
                    end=None,
                    project_id=None,
                    q_filter=None):
        return self._get_data('compute',
                              start,
                              end,
                              project_id,
                              q_filter)

    def get_image(self,
                  start,
                  end=None,
                  project_id=None,
                  q_filter=None):
        return self._get_data('image',
                              start,
                              end,
                              project_id,
                              q_filter)

    def get_volume(self,
                   start,
                   end=None,
                   project_id=None,
                   q_filter=None):
        return self._get_data('volume',
                              start,
                              end,
                              project_id,
                              q_filter)

    def get_network_bw_in(self,
                          start,
                          end=None,
                          project_id=None,
                          q_filter=None):
        return self._get_data('network.bw.in',
                              start,
                              end,
                              project_id,
                              q_filter)

    def get_network_bw_out(self,
                           start,
                           end=None,
                           project_id=None,
                           q_filter=None):
        return self._get_data('network.bw.out',
                              start,
                              end,
                              project_id,
                              q_filter)

    def get_network_floating(self,
                             start,
                             end=None,
                             project_id=None,
                             q_filter=None):
        return self._get_data('network.floating',
                              start,
                              end,
                              project_id,
                              q_filter)
