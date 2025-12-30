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
import cotyledon
from cotyledon import oslo_config_glue
from oslo_config import cfg
from oslo_log import log

from cloudkitty import service


CONF = cfg.CONF
LOG = log.getLogger(__name__)


def main():
    sm = cotyledon.ServiceManager()
    service.prepare_service()
    oslo_config_glue.setup(sm, CONF)

    # NOTE(mc): This import is done here to ensure that the prepare_service()
    # function is called before any cfg option. By importing the orchestrator
    # file, the utils one is imported too, and then some cfg options are read
    # before the prepare_service(), making cfg.CONF returning default values
    # systematically.
    from cloudkitty import orchestrator

    if CONF.orchestrator.max_workers:
        sm.add(
            orchestrator.CloudKittyProcessor,
            workers=CONF.orchestrator.max_workers)
    else:
        LOG.info("No worker configured for CloudKitty processing.")

    if CONF.orchestrator.max_workers_reprocessing:
        sm.add(
            orchestrator.CloudKittyReprocessor,
            workers=CONF.orchestrator.max_workers_reprocessing)
    else:
        LOG.info("No worker configured for CloudKitty reprocessing.")

    sm.run()


if __name__ == '__main__':
    main()
