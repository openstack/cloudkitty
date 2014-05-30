#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: billing/base.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, Billing processor base class.
"""


class BaseBillingProcessor(object):
    def __init__(self):
        raise NotImplementedError()

    def process(self, data):
        raise NotImplementedError()
