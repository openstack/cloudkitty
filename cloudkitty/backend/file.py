#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: backend/file.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, Simple file backend
"""


class FileBackend(file):
    def __init__(self, path, mode='ab+'):
        try:
            super(FileBackend, self).__init__(path, mode)
        except IOError:
            # File not found
            super(FileBackend, self).__init__(path, 'wb+')
