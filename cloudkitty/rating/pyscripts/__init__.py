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
from cloudkitty import dataframe
from cloudkitty import rating
from cloudkitty.rating.pyscripts.controllers import root as root_api
from cloudkitty.rating.pyscripts.db import api as pyscripts_db_api

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


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
        # current scripts loaded to memory
        self._scripts = {}

        self.load_scripts_in_memory()
        super(PyScripts, self).__init__(tenant_id)

    def load_scripts_in_memory(self):
        db = pyscripts_db_api.get_instance()
        scripts_uuid_list = db.list_scripts()
        self.purge_removed_scripts(scripts_uuid_list)

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

    def purge_removed_scripts(self, scripts_uuid_list):
        scripts_to_purge = self.get_all_script_to_remove(scripts_uuid_list)
        self.remove_purged_scripts(scripts_to_purge)

    def get_all_script_to_remove(self, new_scripts_uuid_list):
        scripts_to_purge = []
        for script_uuid in self._scripts.keys():
            if script_uuid not in new_scripts_uuid_list:
                scripts_to_purge.append(script_uuid)
        return scripts_to_purge

    def remove_purged_scripts(self, scripts_to_purge):
        for script_uuid in scripts_to_purge:
            LOG.info("Removing script [%s] from the script list to execute.",
                     self._scripts[script_uuid])

            del self._scripts[script_uuid]

    def reload_config(self):
        """Reload the module's configuration.

        """
        LOG.debug("Executing the reload of configurations.")
        self.load_scripts_in_memory()
        LOG.debug("Configurations reloaded.")

    def start_script(self, code, data):
        context = {'data': data}
        exec(code, context)  # nosec
        return context['data']

    def process(self, data):
        for script in self._scripts.values():
            data_dict = data.as_dict(mutable=True)
            LOG.debug("Executing pyscript [%s] with data [%s].",
                      script, data_dict)

            data_output = self.start_script(script['code'], data_dict)

            LOG.debug("Result [%s] for processing with pyscript [%s] with "
                      "data [%s].", data_output, script, data_dict)

            data = dataframe.DataFrame.from_dict(data_output)
        return data
