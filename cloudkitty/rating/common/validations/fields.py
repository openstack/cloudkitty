# -*- coding: utf-8 -*-
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

from oslo_log import log as logging


LOG = logging.getLogger(__name__)


def _resource_changed(current_resource, resource, ignore_attribute_check=None):
    if not ignore_attribute_check:
        ignore_attribute_check = []
    resource_attributes = resource._wsme_attributes
    for attribute in resource_attributes:
        new_value = getattr(resource, attribute.key, None)
        old_value = getattr(current_resource, attribute.key, None)
        if attribute.key in ignore_attribute_check:
            continue

        if new_value and new_value != old_value:
            return True

    return False


def validate_update_allowing_only_end_date(current_resource, resource):
    now = datetime.datetime.now()
    if current_resource.start < now:
        if current_resource.end is None:
            if _resource_changed(current_resource, resource,
                                 ignore_attribute_check=["end"]):
                pecan.abort(
                    400, f'You are allowed to update '
                         f'only the attribute [end] as this rule is '
                         f'already running as it started on '
                         f'[{current_resource.start}]')

            if resource.end and resource.end < now:
                pecan.abort(
                    400, f'End date must be in the future. '
                         f'end=[{resource.end}] current time=[{now}]')
            return True

        pecan.abort(
            400, 'Cannot update a rule that was already processed and '
                 'has a defined end date.')

    else:
        LOG.debug("Updating the rating rule [%s] with new data [%s] as it has "
                  "not been used yet.", current_resource, resource)

    resource.name = None
    if not resource.start:
        resource.start = current_resource.start
    validate_resource(resource)
    return False


def validate_resource(resource, force=False):
    start = resource.start
    end = resource.end
    now = datetime.datetime.now()
    if not force and start and start < now:
        pecan.abort(
            400, f'Cannot create a rule with start in the past. '
                 f'start=[{start}] current time=[{now}].')
    if end and end < start:
        pecan.abort(
            400, f'Cannot create a rule with start after end. '
                 f'start=[{start}] end=[{end}].')
    if force:
        LOG.info("Creating resource [%s] at [%s] with start date [%s] using "
                 "the flag 'Force'.", resource, now, start)
