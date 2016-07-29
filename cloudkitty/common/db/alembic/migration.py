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
import os

import alembic
from alembic import config as alembic_config

ALEMBIC_INI_PATH = os.path.join(os.path.dirname(__file__), 'alembic.ini')


def load_alembic_config(repo_path, ini_path=ALEMBIC_INI_PATH):
    if not os.path.exists(repo_path):
        raise Exception('Repo path (%s) not found.' % repo_path)
    if not os.path.exists(ini_path):
        raise Exception('Ini path (%s) not found.' % ini_path)
    config = alembic_config.Config(ini_path)
    config.set_main_option('script_location', repo_path)
    return config


def upgrade(config, version):
    return alembic.command.upgrade(config, version or 'head')


def version(config):
    return alembic.command.current(config)


def revision(config, message='', autogenerate=False):
    """Creates template for migration.

    :param message: Text that will be used for migration title
    :type message: string
    :param autogenerate: If True - generates diff based on current database
                            state
    :type autogenerate: bool
    """
    return alembic.command.revision(config, message=message,
                                    autogenerate=autogenerate)


def stamp(config, revision):
    """Stamps database with provided revision.

    :param revision: Should match one from repository or head - to stamp
                        database with most recent revision
    :type revision: string
    """
    return alembic.command.stamp(config, revision=revision)
