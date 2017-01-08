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
# @author: Gauvain Pocentek
#
from keystonemiddleware import auth_token


class AuthTokenMiddleware(auth_token.AuthProtocol):
    """A subclass of keystone auth_token middleware.

    It avoids authentication on public routes.
    """

    def __init__(self, app, conf, public_api_routes=[]):
        self._public_routes = public_api_routes
        super(AuthTokenMiddleware, self).__init__(app, conf)

    def __call__(self, env, start_response):
        # Strip the / from the URL if we're not dealing with '/'
        path = env.get('PATH_INFO').rstrip('/') or '/'

        if path in self._public_routes:
            return self._app(env, start_response)

        return super(AuthTokenMiddleware, self).__call__(env, start_response)

    @classmethod
    def factory(cls, global_config, **local_conf):
        public_routes = local_conf.get('acl_public_routes', '')
        public_api_routes = [path.strip() for path in public_routes.split(',')]

        def _factory(app):
            return cls(app, global_config, public_api_routes=public_api_routes)
        return _factory
