# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
import itertools

import cloudkitty.api.app
import cloudkitty.collector.gnocchi
import cloudkitty.collector.prometheus
import cloudkitty.config
import cloudkitty.fetcher
import cloudkitty.fetcher.gnocchi
import cloudkitty.fetcher.keystone
import cloudkitty.fetcher.prometheus
import cloudkitty.fetcher.source
import cloudkitty.orchestrator
import cloudkitty.service
import cloudkitty.storage
import cloudkitty.storage.v1.hybrid.backends.gnocchi
import cloudkitty.storage.v2.elasticsearch
import cloudkitty.storage.v2.influx
import cloudkitty.storage.v2.opensearch
import cloudkitty.utils

__all__ = ['list_opts']

_opts = [
    ('api', list(itertools.chain(
        cloudkitty.api.app.api_opts,))),
    ('collect', list(itertools.chain(
        cloudkitty.collector.collect_opts))),
    ('collector_gnocchi', list(itertools.chain(
        cloudkitty.collector.gnocchi.collector_gnocchi_opts))),
    ('collector_prometheus', list(itertools.chain(
        cloudkitty.collector.prometheus.collector_prometheus_opts))),
    ('fetcher', list(itertools.chain(
        cloudkitty.fetcher.fetcher_opts))),
    ('fetcher_gnocchi', list(itertools.chain(
        cloudkitty.fetcher.gnocchi.gfetcher_opts,
        cloudkitty.fetcher.gnocchi.fetcher_gnocchi_opts))),
    ('fetcher_keystone', list(itertools.chain(
        cloudkitty.fetcher.keystone.fetcher_keystone_opts))),
    ('fetcher_prometheus', list(itertools.chain(
        cloudkitty.fetcher.prometheus.fetcher_prometheus_opts))),
    ('fetcher_source', list(itertools.chain(
        cloudkitty.fetcher.source.fetcher_source_opts))),
    ('orchestrator', list(itertools.chain(
        cloudkitty.orchestrator.orchestrator_opts))),
    ('output', list(itertools.chain(
        cloudkitty.config.output_opts))),
    ('state', list(itertools.chain(
        cloudkitty.config.state_opts))),
    ('storage', list(itertools.chain(
        cloudkitty.storage.storage_opts))),
    ('storage_influxdb', list(itertools.chain(
        cloudkitty.storage.v2.influx.influx_storage_opts))),
    ('storage_elasticsearch', list(itertools.chain(
        cloudkitty.storage.v2.elasticsearch.elasticsearch_storage_opts))),
    ('storage_opensearch', list(itertools.chain(
        cloudkitty.storage.v2.opensearch.opensearch_storage_opts))),
    ('storage_gnocchi', list(itertools.chain(
        cloudkitty.storage.v1.hybrid.backends.gnocchi.gnocchi_storage_opts))),
    (None, list(itertools.chain(
        cloudkitty.api.app.auth_opts,
        cloudkitty.service.service_opts))),
]


def list_opts():
    return [(g, copy.deepcopy(o)) for g, o in _opts]
