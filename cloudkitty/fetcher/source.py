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
from oslo_config import cfg

from cloudkitty import fetcher

FETCHER_SOURCE_OPTS = 'fetcher_source'

fetcher_source_opts = [
    cfg.ListOpt(
        'sources',
        default=list(),
        help='list of source identifiers',
    ),
]

cfg.CONF.register_opts(fetcher_source_opts, FETCHER_SOURCE_OPTS)

CONF = cfg.CONF


class SourceFetcher(fetcher.BaseFetcher):
    """Source projects fetcher."""

    name = 'source'

    def get_tenants(self):
        return CONF.fetcher_source.sources
