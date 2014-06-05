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
import json


class StateManager(object):
    def __init__(self, state_backend, state_basepath, user_id, report_type,
                 distributed=False):
        self._backend = state_backend
        self._basepath = state_basepath
        self._uid = user_id
        self._type = report_type
        self._distributed = distributed

        # States
        self._ts = None
        self._metadata = {}

    def _gen_filename(self):
        filename = '{}_{}.state'.format(self._type, self._uid)
        return filename

    def _open(self, mode='rb'):
        filename = self._gen_filename()
        state_file = self._backend(filename, mode)
        return state_file

    def _load(self):
        try:
            state_file = self._open()
            state_data = json.loads(state_file.read())
            self._ts = state_data['timestamp']
            self._metadata = state_data['metadata']
            state_file.close()
        except IOError:
            pass

    def _update(self):
        state_file = self._open('wb')
        state_data = {'timestamp': self._ts,
                      'metadata': self._metadata}
        state_file.write(json.dumps(state_data))
        state_file.close()

    def set_state(self, timestamp):
        """
        Set the current state's timestamp
        """
        if self._distributed:
            self._load()
        self._ts = timestamp
        self._update()

    def get_state(self):
        """
        Get the state timestamp
        """
        if self._distributed:
            self._load()
        return self._ts

    def set_metadata(self, metadata):
        """
        Set metadata attached to the state
        """
        if self._distributed:
            self._load()
        self._metadata = metadata
        self._update()

    def get_metadata(self):
        """
        Get metadata attached to the state
        """
        if self._distributed:
            self._load()
        return self._metadata
