# -*- coding: utf-8 -*-
# !/usr/bin/env python
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
# @author: Stéphane Albert
#
from __future__ import print_function
import datetime
import sys
import time

from keystoneclient.v2_0 import client as kclient
from oslo.config import cfg
from stevedore import driver
from stevedore import named

from cloudkitty import config  # NOQA
from cloudkitty import extension_manager
from cloudkitty.openstack.common import importutils as i_utils
from cloudkitty.openstack.common import log as logging
from cloudkitty import state
from cloudkitty import write_orchestrator as w_orch


LOG = logging.getLogger(__name__)


CONF = cfg.CONF


class Orchestrator(object):
    def __init__(self):
        self.keystone = kclient.Client(username=CONF.auth.username,
                                       password=CONF.auth.password,
                                       tenant_name=CONF.auth.tenant,
                                       region_name=CONF.auth.region,
                                       auth_url=CONF.auth.url)

        s_backend = i_utils.import_class(CONF.state.backend)
        self.sm = state.DBStateManager(self.keystone.user_id,
                                       'osrtf')

        collector_args = {'user': CONF.auth.username,
                          'password': CONF.auth.password,
                          'tenant': CONF.auth.tenant,
                          'region': CONF.auth.region,
                          'keystone_url': CONF.auth.url,
                          'period': CONF.collect.period}
        self.collector = driver.DriverManager(
            'cloudkitty.collector.backends',
            CONF.collect.collector,
            invoke_on_load=True,
            invoke_kwds=collector_args).driver

        w_backend = i_utils.import_class(CONF.output.backend)
        self.wo = w_orch.WriteOrchestrator(w_backend,
                                           s_backend,
                                           self.keystone.user_id,
                                           self.sm,
                                           basepath=CONF.output.basepath)

        # Billing processors
        self.b_processors = {}
        self._load_billing_processors()

        # Output settings
        output_pipeline = named.NamedExtensionManager(
            'cloudkitty.output.writers',
            CONF.output.pipeline)
        for writer in output_pipeline:
            self.wo.add_writer(writer.plugin)

    def _check_state(self):
        def _get_this_month_timestamp():
            now = datetime.datetime.now()
            month_start = datetime.datetime(now.year, now.month, 1)
            timestamp = int(time.mktime(month_start.timetuple()))
            return timestamp

        timestamp = self.sm.get_state()
        if not timestamp:
            return _get_this_month_timestamp()

        now = int(time.time())
        if timestamp + CONF.collect.period < now:
            return timestamp
        return 0

    def _collect(self, service, start_timestamp):
        next_timestamp = start_timestamp + CONF.collect.period
        raw_data = self.collector.retrieve(service,
                                           start_timestamp,
                                           next_timestamp)

        timed_data = [{'period': {'begin': start_timestamp,
                                  'end': next_timestamp},
                      'usage': raw_data}]
        return timed_data

    def _load_billing_processors(self):
        self.b_processors = {}
        processors = extension_manager.EnabledExtensionManager(
            'cloudkitty.billing.processors',
        )

        for processor in processors:
            b_name = processor.name
            b_obj = processor.obj
            self.b_processors[b_name] = b_obj

    def process(self):
        while True:
            timestamp = self._check_state()
            if not timestamp:
                print("Nothing left to do.")
                break

            for service in CONF.collect.services:
                data = self._collect(service, timestamp)

                # Billing
                for processor in self.b_processors.values():
                    processor.process(data)

                # Writing
                self.wo.append(data)

            # We're getting a full period so we directly commit
            self.wo.commit()

        self.wo.close()


def main():
    CONF(sys.argv[1:], project='cloudkitty')
    logging.setup('cloudkitty')
    orchestrator = Orchestrator()
    orchestrator.process()


if __name__ == "__main__":
    main()
