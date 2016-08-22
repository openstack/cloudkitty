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

from cloudkitty.common.db.alembic import migration

ALEMBIC_REPO = os.path.join(os.path.dirname(__file__), 'alembic')


def upgrade(revision):
    config = migration.load_alembic_config(ALEMBIC_REPO)
    return migration.upgrade(config, revision)


def version():
    config = migration.load_alembic_config(ALEMBIC_REPO)
    return migration.version(config)


def revision(message, autogenerate):
    config = migration.load_alembic_config(ALEMBIC_REPO)
    return migration.revision(config, message, autogenerate)


def stamp(revision):
    config = migration.load_alembic_config(ALEMBIC_REPO)
    return migration.stamp(config, revision)
