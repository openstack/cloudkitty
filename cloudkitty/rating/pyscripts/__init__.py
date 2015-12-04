# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
from cloudkitty import rating
from cloudkitty.rating.pyscripts.controllers import root as root_api
from cloudkitty.rating.pyscripts.db import api as pyscripts_db_api


class PyScripts(rating.RatingProcessorBase):
    """PyScripts rating module.

    PyScripts is a module made to execute custom made python scripts to create
    rating policies.
    """

    module_name = 'pyscripts'
    description = 'PyScripts rating module.'
    hot_config = True
    config_controller = root_api.PyScriptsConfigController

    db_api = pyscripts_db_api.get_instance()

    def __init__(self, tenant_id=None):
        self._scripts = {}
        self.load_scripts_in_memory()
        super(PyScripts, self).__init__(tenant_id)

    def load_scripts_in_memory(self):
        db = pyscripts_db_api.get_instance()
        scripts_uuid_list = db.list_scripts()
        # Purge old entries
        scripts_to_purge = []
        for script_uuid in self._scripts.keys():
            if script_uuid not in scripts_uuid_list:
                scripts_to_purge.append(script_uuid)
        for script_uuid in scripts_to_purge:
            del self._scripts[script_uuid]
        # Load or update script
        for script_uuid in scripts_uuid_list:
            script_db = db.get_script(uuid=script_uuid)
            name = script_db.name
            checksum = script_db.checksum
            if name not in self._scripts:
                self._scripts[script_uuid] = {}
            script = self._scripts[script_uuid]
            # NOTE(sheeprine): We're doing this the easy way, we might want to
            # store the context and call functions in future
            if script.get(checksum, '') != checksum:
                code = compile(
                    script_db.data,
                    '<PyScripts: {name}>'.format(name=name),
                    'exec')
                script.update({
                    'name': name,
                    'code': code,
                    'checksum': checksum})

    def reload_config(self):
        """Reload the module's configuration.

        """
        self.load_scripts_in_memory()

    def start_script(self, code, data):
        context = {'data': data}
        exec(code, context)
        return data

    def process(self, data):
        for script in self._scripts.values():
            self.start_script(script['code'], data)
        return data
