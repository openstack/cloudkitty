# -*- coding: utf8 -*-
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
