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
import sys
import time

import iso8601


def dt2ts(orig_dt):
    return int(time.mktime(orig_dt.timetuple()))


def iso2dt(iso_date):
    return iso8601.parse_date(iso_date)


def import_class(import_str):
    mod_str, _sep, class_str = import_str.rpartition('.')
    if not mod_str:
        mod_str = '__builtin__'
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ValueError, AttributeError):
        raise ImportError('Class %s cannot be found.' % class_str)
