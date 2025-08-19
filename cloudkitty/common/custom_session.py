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
import pecan
import requests

from keystoneauth1 import loading as ks_loading
from keystoneauth1 import session as ks_session
from keystoneclient.v3 import client as ks_client
from oslo_config import cfg

LOG = logging.getLogger(__name__)


def create_custom_session(session_options, pool_size):
    LOG.debug("Using custom connection pool size: %s", pool_size)
    session = requests.Session()
    session.adapters['http://'] = ks_session.TCPKeepAliveAdapter(
        pool_maxsize=pool_size)
    session.adapters['https://'] = ks_session.TCPKeepAliveAdapter(
        pool_maxsize=pool_size)

    return ks_session.Session(session=session, **session_options)


def get_request_user():
    conf = cfg.CONF
    ks_auth = ks_loading.load_auth_from_conf_options(
        conf, 'keystone_authtoken')
    session = create_custom_session(
        {'auth': ks_auth, 'verify': False}, 1)

    keystone_client = ks_client.Client(
        session=session,
        interface=conf['keystone_authtoken'].interface)

    keystone_token = pecan.request.headers.get('X-Auth-Token')
    if not keystone_token:
        LOG.debug("There is no auth token in the request header, using "
                  "'unknown' as the request user.")
        return 'unknown'
    token_data = ks_client.tokens.TokenManager(
        keystone_client).get_token_data(
        keystone_token)
    session.session.close()
    return token_data['token']['user']['id']
