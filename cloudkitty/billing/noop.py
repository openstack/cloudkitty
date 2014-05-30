#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: billing/noop.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, Dummy NOOP Billing Processor
"""
from cloudkitty.billing.base import BaseBillingProcessor


class Noop(BaseBillingProcessor):
    def __init__(self):
        pass

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service in cur_usage:
                for entry in cur_usage[service]:
                    if 'billing' not in entry:
                        entry['billing'] = {}
        return data
