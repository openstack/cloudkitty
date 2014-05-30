#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: state.py
Author: Stephane Albert
Email: stephane.albert@objectif-libre.com
Github: http://github.com/objectiflibre
Description: CloudKitty, State tracking
"""
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
