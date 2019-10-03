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
import flask_restful
from werkzeug import exceptions as http_exceptions

from cloudkitty.common import policy
from cloudkitty import storage


class BaseResource(flask_restful.Resource):
    """Base class for all cloudkitty v2 API resources.

    Returns a 403 Forbidden HTTP code in case a ``PolicyNotAuthorized``
    exception is raised by the API method.
    """

    def dispatch_request(self, *args, **kwargs):
        try:
            return super(BaseResource, self).dispatch_request(*args, **kwargs)
        except policy.PolicyNotAuthorized:
            raise http_exceptions.Forbidden(
                "You are not authorized to perform this action")

    @classmethod
    def reload(cls):
        """Reloads all required drivers"""
        cls._storage = storage.get_storage()

    @classmethod
    def load(cls):
        """Loads all required drivers.

        If the drivers are already loaded, does nothing.
        """
        if not getattr(cls, '_loaded', False):
            cls.reload()
            cls._loaded = True

    def __init__(self, *args, **kwargs):
        super(BaseResource, self).__init__(*args, **kwargs)
        self.load()
