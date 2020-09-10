# -*- coding: utf-8 -*-
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
import logging
import requests

from keystoneauth1 import session as ks_session


LOG = logging.getLogger(__name__)


def create_custom_session(session_options, pool_size):
    LOG.debug("Using custom connection pool size: %s", pool_size)
    session = requests.Session()
    session.adapters['http://'] = ks_session.TCPKeepAliveAdapter(
        pool_maxsize=pool_size)
    session.adapters['https://'] = ks_session.TCPKeepAliveAdapter(
        pool_maxsize=pool_size)

    return ks_session.Session(session=session, **session_options)
