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
import datetime
import pecan
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1 import types as ck_types
from cloudkitty.common.custom_session import get_request_user
from cloudkitty import rating
from cloudkitty.rating.common.validations import fields as field_validations
from cloudkitty.rating.pyscripts.datamodels import script as script_models
from cloudkitty.rating.pyscripts.db import api as db_api


class PyScriptsScriptsController(rating.RatingRestControllerBase):
    """Controller responsible of scripts management.

    """

    def normalize_data(self, data):
        """Translate data to binary format if needed.

        :param data: Data to convert to binary type.
        """
        if data == wtypes.Unset:
            return ''
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        return data

    @wsme_pecan.wsexpose(script_models.ScriptCollection,
                         bool,
                         bool,
                         datetime.datetime,
                         datetime.datetime,
                         str,
                         str,
                         str,
                         str,
                         bool)
    def get_all(self, no_data=False,
                deleted=False,
                start=None,
                end=None,
                updated_by=None,
                created_by=None,
                deleted_by=None,
                description=None,
                is_active=None):
        """Get the script list

        :param no_data: Set to True to remove script data from output.
        :param deleted: Show deleted mappings.
        :param start: Mappings with start after date.
        :param end: Mappings with end before date.
        :param updated_by: user uuid to filter on.
        :param created_by: user uuid to filter on.
        :param deleted_by: user uuid to filter on.
        :param description: mapping that contains the text in description.
        :param is_active: only active mappings.
        :return: List of every scripts.
        """
        pyscripts = db_api.get_instance()
        script_list = []
        script_uuid_list = pyscripts.list_scripts(
            deleted=deleted,
            start=start,
            end=end,
            updated_by=updated_by,
            created_by=created_by,
            deleted_by=deleted_by,
            description=description,
            is_active=is_active)
        for script_uuid in script_uuid_list:
            script_db = pyscripts.get_script(uuid=script_uuid,
                                             deleted=deleted)
            script = script_db.export_model()
            if no_data:
                del script['data']
            script_list.append(script_models.Script(
                **script))
        res = script_models.ScriptCollection(scripts=script_list)
        return res

    @wsme_pecan.wsexpose(script_models.Script, ck_types.UuidType())
    def get_one(self, script_id):
        """Return a script.

        :param script_id: UUID of the script to filter on.
        """
        pyscripts = db_api.get_instance()
        try:
            script_db = pyscripts.get_script(uuid=script_id)
            return script_models.Script(**script_db.export_model())
        except db_api.NoSuchScript as e:
            pecan.abort(404, e.args[0])

    @wsme_pecan.wsexpose(script_models.Script,
                         bool,
                         body=script_models.Script,
                         status_code=201)
    def post(self, force=False, script_data=None):
        """Create pyscripts script.

        :param force: Allows start and end in the past.
        :param script_data: Informations about the script to create.
        """
        pyscripts = db_api.get_instance()
        field_validations.validate_resource(
            script_data, force=force)
        try:
            created_by = get_request_user()
            data = self.normalize_data(script_data.data)
            script_db = pyscripts.create_script(
                script_data.name, data,
                created_by=created_by,
                start=script_data.start,
                end=script_data.end,
                description=script_data.description)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += script_db.script_id
            return script_models.Script(
                **script_db.export_model())
        except db_api.ScriptAlreadyExists as e:
            pecan.abort(409, e.args[0])

    @wsme_pecan.wsexpose(script_models.Script,
                         ck_types.UuidType(),
                         body=script_models.Script,
                         status_code=201)
    def put(self, script_id, script_data):
        """Update pyscripts script.

        :param script_id: UUID of the script to update.
        :param script_data: Script data to update.
        """
        pyscripts = db_api.get_instance()
        try:
            updated_by = get_request_user()
            current_script = pyscripts.get_script(uuid=script_id)
            data = self.normalize_data(script_data.data)
            if field_validations.validate_update_allowing_only_end_date(
                    current_script,
                    script_data):
                script_db = pyscripts.update_script(
                    script_id, end=script_data.end,
                    updated_by=updated_by)
            else:
                script_db = pyscripts.update_script(
                    script_id, data=data, updated_by=updated_by,
                    end=script_data.end,
                    description=script_data.description,
                    start=script_data.start)
            pecan.response.location = pecan.request.path_url
            if pecan.response.location[-1] != '/':
                pecan.response.location += '/'
            pecan.response.location += script_db.script_id
            return script_models.Script(
                **script_db.export_model())
        except db_api.NoSuchScript as e:
            pecan.abort(404, e.args[0])

    @wsme_pecan.wsexpose(None, ck_types.UuidType(), status_code=204)
    def delete(self, script_id):
        """Delete the script.

        :param script_id: UUID of the script to delete.
        """
        pyscripts = db_api.get_instance()
        deleted_by = get_request_user()
        try:
            pyscripts.delete_script(uuid=script_id, deleted_by=deleted_by)
        except db_api.NoSuchScript as e:
            pecan.abort(404, e.args[0])
