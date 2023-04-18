# Copyright 2019 Objectif Libre
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


class BaseOpenSearchException(Exception):
    """Base exception raised by the OpenSearch v2 storage driver"""


class InvalidStatusCode(BaseOpenSearchException):
    def __init__(self, expected, actual, msg, query):
        super(InvalidStatusCode, self).__init__(
            "Expected {} status code, got {}: {}. Query was {}".format(
                expected, actual, msg, query))


class IndexDoesNotExist(BaseOpenSearchException):
    def __init__(self, index_name):
        super(IndexDoesNotExist, self).__init__(
            "OpenSearch index {} does not exist".format(index_name)
        )
