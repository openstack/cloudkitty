# Copyright 2016 Hewlett Packard Enterprise Development Corporation, LP
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


from oslo_config import cfg
from oslo_middleware import cors
from oslo_policy import opts as policy_opts


def set_config_defaults():
    """This method updates all configuration default values."""
    set_cors_middleware_defaults()

    # TODO(gmann): Remove setting the default value of config policy_file
    # once oslo_policy change the default value to 'policy.yaml'.
    # https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
    DEFAULT_POLICY_FILE = 'policy.yaml'
    policy_opts.set_defaults(cfg.CONF, DEFAULT_POLICY_FILE)


def set_cors_middleware_defaults():
    """Update default configuration options for oslo.middleware."""
    cors.set_defaults(
        allow_headers=['X-Auth-Token',
                       'X-Subject-Token',
                       'X-Roles',
                       'X-User-Id',
                       'X-Domain-Id',
                       'X-Project-Id',
                       'X-Tenant-Id',
                       'X-OpenStack-Request-ID'],
        expose_headers=['X-Auth-Token',
                        'X-Subject-Token',
                        'X-Service-Token',
                        'X-OpenStack-Request-ID'],
        allow_methods=['GET',
                       'PUT',
                       'POST',
                       'DELETE',
                       'PATCH'])
