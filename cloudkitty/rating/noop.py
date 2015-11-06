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
import decimal

from cloudkitty import rating


class Noop(rating.RatingProcessorBase):

    module_name = "noop"
    description = 'Dummy test module.'

    @property
    def enabled(self):
        """Check if the module is enabled

        :returns: bool if module is enabled
        """
        return True

    @property
    def priority(self):
        return 1

    def reload_config(self):
        pass

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service in cur_usage:
                for entry in cur_usage[service]:
                    if 'rating' not in entry:
                        entry['rating'] = {'price': decimal.Decimal(0)}
        return data
