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
from pecan import rest

from cloudkitty.api.v1.controllers import collector as collector_api
from cloudkitty.api.v1.controllers import info as info_api
from cloudkitty.api.v1.controllers import rating as rating_api
from cloudkitty.api.v1.controllers import report as report_api
from cloudkitty.api.v1.controllers import storage as storage_api


class V1Controller(rest.RestController):
    """API version 1 controller.

    """

    billing = rating_api.RatingController()
    collector = collector_api.CollectorController()
    rating = rating_api.RatingController()
    report = report_api.ReportController()
    storage = storage_api.StorageController()
    info = info_api.InfoController()
