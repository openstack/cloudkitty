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
from stevedore import enabled


class EnabledExtensionManager(enabled.EnabledExtensionManager):
    """CloudKitty Rating processor manager

    Override default EnabledExtensionManager to check for an internal
    object property in the extension.
    """

    def __init__(self, namespace, invoke_args=(), invoke_kwds={}):

        def check_enabled(ext):
            """Check if extension is enabled.

            """
            return ext.obj.enabled

        super(EnabledExtensionManager, self).__init__(
            namespace=namespace,
            check_func=check_enabled,
            invoke_on_load=True,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwds,
        )
