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
