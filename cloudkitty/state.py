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
import decimal
import json

from cloudkitty.db import api


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

        # Load states
        self._load()

    def _gen_filename(self):
        # FIXME(sheeprine): Basepath can't be enforced at the moment
        filename = '{0}_{1}.state'.format(self._type,
                                          self._uid)
        return filename

    def _open(self, mode='rb'):
        filename = self._gen_filename()
        state_file = self._backend(filename, mode)
        return state_file

    def _load(self):
        try:
            state_file = self._open()
            raw_data = state_file.read()
            if raw_data:
                state_data = json.loads(raw_data)
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
        """Set the current state's timestamp."""
        if self._distributed:
            self._load()
        self._ts = timestamp
        self._update()

    def get_state(self):
        """Get the state timestamp."""
        if self._distributed:
            self._load()
        return self._ts

    def set_metadata(self, metadata):
        """Set metadata attached to the state."""
        if self._distributed:
            self._load()
        self._metadata = metadata
        self._update()

    def get_metadata(self):
        """Get metadata attached to the state."""
        if self._distributed:
            self._load()
        return self._metadata


class DecimalJSONEncoder(json.JSONEncoder):
    """Wrapper class to handle decimal.Decimal objects in json.dumps()."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalJSONEncoder, self).default(obj)


class DBStateManager(object):
    def __init__(self, user_id, report_type, distributed=False):
        self._state_name = self._gen_name(report_type, user_id)
        self._distributed = distributed
        self._db = api.get_instance().get_state()

    def _gen_name(self, state_type, uid):
        name = '{0}_{1}'.format(state_type, uid)
        return name

    def get_state(self):
        """Get the state timestamp."""

        return self._db.get_state(self._state_name)

    def set_state(self, timestamp):
        """Set the current state's timestamp."""

        self._db.set_state(self._state_name, timestamp)

    def get_metadata(self):
        """Get metadata attached to the state."""

        data = self._db.get_metadata(self._state_name)
        if data:
            return json.loads(data)

    def set_metadata(self, metadata):
        """Set metadata attached to the state."""

        self._db.set_metadata(self._state_name,
                              json.dumps(metadata, cls=DecimalJSONEncoder))
