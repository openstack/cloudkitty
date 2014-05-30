#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: billing/hash.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, HashMap Billing processor.
"""
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
