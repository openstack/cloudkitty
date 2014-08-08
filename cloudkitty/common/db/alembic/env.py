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
from logging import config as log_config

from alembic import context

from cloudkitty import db

config = context.config
log_config.fileConfig(config.config_file_name)


def run_migrations_online(target_metadata, version_table):
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    :param target_metadata: Model's metadata used for autogenerate support.
    :param version_table: Override the default version table for alembic.
    """
    engine = db.get_engine()
    with engine.connect() as connection:
        context.configure(connection=connection,
                          target_metadata=target_metadata,
                          version_table=version_table)
        with context.begin_transaction():
            context.run_migrations()
