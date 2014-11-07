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
import calendar
import datetime
import time

import iso8601


def dt2ts(orig_dt):
    return int(time.mktime(orig_dt.timetuple()))


def iso2dt(iso_date):
    return iso8601.parse_date(iso_date)


def get_this_month():
    now = datetime.datetime.utcnow()
    month_start = datetime.datetime(now.year, now.month, 1)
    return month_start


def get_this_month_timestamp():
    return dt2ts(get_this_month())


def get_next_month():
    start_dt = get_this_month()
    next_dt = start_dt + datetime.timedelta(calendar.mdays[start_dt.month])
    return next_dt


def get_next_month_timestamp():
    return dt2ts(get_next_month())
