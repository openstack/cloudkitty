# -*- coding: utf-8 -*-
# !/usr/bin/env python
# Copyright 2015 Objectif Libre
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
# @author: Martin CAMEY
#
import hashlib

from cloudkitty import fetcher


class SourceFetcher(fetcher.BaseFetcher):
    """Source projects fetcher."""

    name = 'source'

    def get_projects(self, conf=None):
        if conf:
            tmp = hashlib.md5()
            tmp.update(conf['name'])
            conf['tenant_id'] = tmp.hexdigest()
        return [conf]

    def get_tenants(self, conf=None):
        return self.get_projects(conf=conf)
