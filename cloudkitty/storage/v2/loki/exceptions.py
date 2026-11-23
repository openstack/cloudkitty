# Copyright 2025 Red Hat
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


class BaseLokiException(Exception):
    """Base exception raised by the Loki v2 storage driver"""


class UnsupportedContentType(BaseLokiException):
    def __init__(self, content_type):
        super(UnsupportedContentType, self).__init__(
            "Content-Type {} is not supported. Use supported formats: "
            "application/json".format(content_type)
        )


class NotImplementedYet(BaseLokiException):
    def __init__(self, method):
        super(NotImplementedYet, self).__init__(
            "Method {} not implemented yet".format(method)
        )


class PushError(BaseLokiException):
    def __init__(self, status_code, response_text):
        self.status_code = status_code
        super(PushError, self).__init__(
            "Failed to push logs to Loki: {} - {}".format(
                status_code, response_text)
        )


class DeleteError(BaseLokiException):
    def __init__(self, status_code, response_text):
        self.status_code = status_code
        super(DeleteError, self).__init__(
            "Failed to delete dataframes from Loki: {} - {}".format(
                status_code, response_text)
        )
