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
# @author: Stéphane Albert
#
from cloudkitty import service


def main():
    service.prepare_service()

    # NOTE(mc): This import is done here to ensure that the prepare_service()
    # function is called before any cfg option. By importing the orchestrator
    # file, the utils one is imported too, and then some cfg options are read
    # before the prepare_service(), making cfg.CONF returning default values
    # systematically.
    from cloudkitty import orchestrator
    processor = orchestrator.Orchestrator()
    try:
        processor.process()
    except KeyboardInterrupt:
        processor.terminate()


if __name__ == '__main__':
    main()
