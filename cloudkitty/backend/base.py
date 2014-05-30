#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: backend/base.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, Base backend (Abstract)
"""


class BaseIOBackend(object):
    def __init__(self, path):
        self.open(path)

    def open(self, path):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def seek(self, offset, from_what=0):
        # 0 beg, 1 cur, 2 end
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError

    def write(self, data):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
