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
import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseIOBackend(object):
    def __init__(self, path):
        self.open(path)

    @abc.abstractmethod
    def open(self, path):
        """Open the connection/file on the backend.

        """

    @abc.abstractmethod
    def tell(self):
        """Current position on the backend.

        """

    @abc.abstractmethod
    def seek(self, offset, from_what=0):
        # 0 beg, 1 cur, 2 end
        """Change position in the backend.

        """

    @abc.abstractmethod
    def flush(self):
        """Force write informations on the backend.

        """

    @abc.abstractmethod
    def write(self, data):
        """Writer data on the backend.

        :param data: Data to be written on the backend.
        """

    @abc.abstractmethod
    def read(self):
        """Read data from the backend.

        :return str: Data read from the backend.
        """

    @abc.abstractmethod
    def close(self):
        """Close the connection/file on the backend.

        """
