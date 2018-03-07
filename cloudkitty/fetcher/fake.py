# -*- coding: utf-8 -*-
# !/usr/bin/env python
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

from oslo_config import cfg

from cloudkitty import fetcher

fake_fetcher_opts = [
    cfg.StrOpt('file',
               default='/var/lib/cloudkitty/tenants.csv',
               help='Fetcher input file.')]

cfg.CONF.register_opts(fake_fetcher_opts, 'fake_fetcher')
CONF = cfg.CONF


class FakeFetcher(fetcher.BaseFetcher):
    """Fake tenants fetcher."""

    def __init__(self):
        filename = cfg.CONF.fake_fetcher.file
        csvfile = open(filename, 'rb')
        reader = csv.DictReader(csvfile)
        self._csv = reader

    def get_tenants(self):
        return [row['id'] for row in self._csv]
