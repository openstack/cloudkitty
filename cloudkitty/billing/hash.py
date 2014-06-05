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
import json

from cloudkitty.billing.base import BaseBillingProcessor


class BasicHashMap(BaseBillingProcessor):
    def __init__(self):
        self._billing_info = {}
        self._load_billing_rates()

    def _load_billing_rates(self):
        # FIXME We should use another path
        self._billing_info = json.loads(open('billing_info.json').read())

    def process_service(self, name, data):
        if name not in self._billing_info:
            return
        serv_b_info = self._billing_info[name]
        for entry in data:
            flat = 0
            rate = 1
            entry_desc = entry['desc']
            for field in serv_b_info:
                if field not in entry_desc:
                    continue
                b_info = serv_b_info[field]
                if b_info['type'] == 'rate':
                    if entry_desc[field] in b_info['map']:
                        rate *= b_info['map'][entry_desc[field]]
                    elif 'default' in b_info['map']:
                        rate *= b_info['map']['default']
                elif b_info['type'] == 'flat':
                    new_flat = 0
                    if entry_desc[field] in b_info['map']:
                        new_flat = b_info['map'][entry_desc[field]]
                    elif 'default' in b_info['map']:
                        new_flat = b_info['map']['default']
                    if new_flat > flat:
                        flat = new_flat
            billing_info = {'price': flat * rate}
            entry['billing'] = billing_info

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service in cur_usage:
                self.process_service(service, cur_usage[service])
        return data
