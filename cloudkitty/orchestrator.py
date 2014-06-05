#!/usr/bin/env python
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
from datetime import datetime
import sys
import time

from keystoneclient.v2_0 import client as kclient
from oslo.config import cfg

import cloudkitty.utils as utils
import cloudkitty.config  # NOQA
from cloudkitty.state import StateManager
from cloudkitty.write_orchestrator import WriteOrchestrator


CONF = cfg.CONF


class Orchestrator(object):
    def __init__(self):
        # Billing settings
        self.billing_pipeline = []
        for billing_processor in CONF.billing.pipeline:
            self.billing_pipeline.append(utils.import_class(billing_processor))
        # Output settings
        self.output_pipeline = []
        for writer in CONF.output.pipeline:
            self.output_pipeline.append(utils.import_class(writer))

        self.keystone = kclient.Client(username=CONF.auth.username,
                                       password=CONF.auth.password,
                                       tenant_name=CONF.auth.tenant,
                                       region_name=CONF.auth.region,
                                       auth_url=CONF.auth.url)

        self.sm = StateManager(utils.import_class(CONF.state.backend),
                               CONF.state.basepath,
                               self.keystone.user_id,
                               'osrtf')

        collector = utils.import_class(CONF.collect.collector)
        self.collector = collector(user=CONF.auth.username,
                                   password=CONF.auth.password,
                                   tenant=CONF.auth.tenant,
                                   region=CONF.auth.region,
                                   keystone_url=CONF.auth.url,
                                   period=CONF.collect.period)

        self.wo = WriteOrchestrator(utils.import_class(CONF.output.backend),
                                    utils.import_class(CONF.state.backend),
                                    self.keystone.user_id,
                                    self.sm)

        for writer in self.output_pipeline:
            self.wo.add_writer(writer)

    def _check_state(self):
        def _get_this_month_timestamp():
            now = datetime.now()
            month_start = datetime(now.year, now.month, 1)
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

    def process(self):
        while True:
            timestamp = self._check_state()
            if not timestamp:
                print "Nothing left to do."
                break

            for service in CONF.collect.services:
                data = self._collect(service, timestamp)

                # Billing
                for b_proc in self.billing_pipeline:
                    b_obj = b_proc()
                    data = b_obj.process(data)

                # Writing
                self.wo.append(data)

            # We're getting a full period so we directly commit
            self.wo.commit()

        self.wo.close()


def main():
    CONF(sys.argv[1:], project='cloudkitty')
    orchestrator = Orchestrator()
    orchestrator.process()


if __name__ == "__main__":
    main()
