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
from oslo_config import cfg
from stevedore import extension

from cloudkitty import config  # noqa
from cloudkitty.db import api as db_api
from cloudkitty import service

CONF = cfg.CONF
PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'


class ModuleNotFound(Exception):
    def __init__(self, name):
        self.name = name
        super(ModuleNotFound, self).__init__(
            "Module %s not found" % name)


class MultipleModulesRevisions(Exception):
    def __init__(self, revision):
        self.revision = revision
        super(MultipleModulesRevisions, self).__init__(
            "Can't apply revision %s to multiple modules." % revision)


class DBCommand(object):

    def __init__(self):
        self.rating_models = {}
        self._load_rating_models()

    def _load_rating_models(self):
        extensions = extension.ExtensionManager(
            PROCESSORS_NAMESPACE)
        self.rating_models = {}
        for ext in extensions:
            if hasattr(ext.plugin, 'db_api'):
                self.rating_models[ext.name] = ext.plugin.db_api

    def get_module_migration(self, name):
        if name == 'cloudkitty':
            mod_migration = db_api.get_instance().get_migration()
        else:
            try:
                module = self.rating_models[name]
                mod_migration = module.get_migration()
            except KeyError:
                raise ModuleNotFound(name)
        return mod_migration

    def get_migrations(self, name=None):
        if not name:
            migrations = []
            migrations.append(self.get_module_migration('cloudkitty'))
            for model in self.rating_models.values():
                migrations.append(model.get_migration())
            return migrations
        else:
            return [self.get_module_migration(name)]

    def check_revsion(self, revision):
        revision = revision or 'head'
        if revision not in ('base', 'head'):
            raise MultipleModulesRevisions(revision)

    def _version_change(self, cmd):
        revision = CONF.command.revision
        module = CONF.command.module
        if not module:
            self.check_revsion(revision)
        migrations = self.get_migrations(module)
        for migration in migrations:
            func = getattr(migration, cmd)
            func(revision)

    def upgrade(self):
        self._version_change('upgrade')

    def revision(self):
        migration = self.get_module_migration(CONF.command.module)
        migration.revision(CONF.command.message, CONF.command.autogenerate)

    def stamp(self):
        migration = self.get_module_migration(CONF.command.module)
        migration.stamp(CONF.command.revision)

    def version(self):
        migration = self.get_module_migration(CONF.command.module)
        migration.version()


def add_command_parsers(subparsers):
    command_object = DBCommand()

    parser = subparsers.add_parser('upgrade')
    parser.set_defaults(func=command_object.upgrade)
    parser.add_argument('--revision', nargs='?')
    parser.add_argument('--module', nargs='?')

    parser = subparsers.add_parser('stamp')
    parser.set_defaults(func=command_object.stamp)
    parser.add_argument('--revision', nargs='?')
    parser.add_argument('--module', required=True)

    parser = subparsers.add_parser('revision')
    parser.set_defaults(func=command_object.revision)
    parser.add_argument('-m', '--message')
    parser.add_argument('--autogenerate', action='store_true')
    parser.add_argument('--module', required=True)

    parser = subparsers.add_parser('version')
    parser.set_defaults(func=command_object.version)
    parser.add_argument('--module', required=True)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    service.prepare_service()
    CONF.command.func()
