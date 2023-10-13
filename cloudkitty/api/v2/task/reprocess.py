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
from datetime import timedelta
from datetimerange import DateTimeRange
import flask
from oslo_log import log
import voluptuous
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy
from cloudkitty import storage_state
from cloudkitty.storage_state.models import ReprocessingScheduler
from cloudkitty.utils import tz as tzutils
from cloudkitty.utils import validation as validation_utils
from oslo_config import cfg


LOG = log.getLogger(__name__)

ALL_SCOPES_OPTION = 'ALL'


def dt_from_iso_as_utc(date_string):
    return tzutils.dt_from_iso(date_string, as_utc=True)


class ReprocessSchedulerPostApi(base.BaseResource):
    def __init__(self, *args, **kwargs):
        super(ReprocessSchedulerPostApi, self).__init__(*args, **kwargs)
        self.storage_state_manager = storage_state.StateManager()
        self.schedule_reprocessing_db = storage_state.ReprocessingSchedulerDb()

    @api_utils.add_input_schema('body', {
        voluptuous.Required('scope_ids'): api_utils.MultiQueryParam(str),
        voluptuous.Required('start_reprocess_time'):
            voluptuous.Coerce(dt_from_iso_as_utc),
        voluptuous.Required('end_reprocess_time'):
            voluptuous.Coerce(dt_from_iso_as_utc),
        voluptuous.Required('reason'): api_utils.SingleQueryParam(str),
    })
    def post(self, scope_ids=[], start_reprocess_time=None,
             end_reprocess_time=None, reason=None):

        policy.authorize(
            flask.request.context,
            'schedule:task_reprocesses',
            {'tenant_id': flask.request.context.project_id or scope_ids}
        )

        ReprocessSchedulerPostApi.validate_inputs(
            end_reprocess_time, reason, scope_ids, start_reprocess_time)

        if ALL_SCOPES_OPTION in scope_ids:
            scope_ids = []

        if not isinstance(scope_ids, list):
            scope_ids = [scope_ids]

        all_scopes_to_reprocess = self.storage_state_manager.get_all(
            identifier=scope_ids, offset=None, limit=None)

        ReprocessSchedulerPostApi.check_if_there_are_invalid_scopes(
            all_scopes_to_reprocess, end_reprocess_time, scope_ids,
            start_reprocess_time)

        ReprocessSchedulerPostApi.validate_start_end_for_reprocessing(
            all_scopes_to_reprocess, end_reprocess_time, start_reprocess_time)

        self.validate_reprocessing_schedules_overlaps(
            all_scopes_to_reprocess, end_reprocess_time, start_reprocess_time)

        for scope in all_scopes_to_reprocess:
            schedule = ReprocessingScheduler(
                identifier=scope.identifier, reason=reason,
                start_reprocess_time=start_reprocess_time,
                end_reprocess_time=end_reprocess_time)

            LOG.debug("Persisting scope reprocessing schedule [%s].", schedule)
            self.schedule_reprocessing_db.persist(schedule)

        return {}, 202

    @staticmethod
    def get_date_period_overflow(date):
        return int(date.timestamp() % cfg.CONF.collect.period)

    @staticmethod
    def get_valid_period_date(date):
        return date - timedelta(
            seconds=ReprocessSchedulerPostApi.get_date_period_overflow(date))

    @staticmethod
    def get_overflow_from_dates(start, end):
        start_overflow = ReprocessSchedulerPostApi.get_date_period_overflow(
            start)
        end_overflow = ReprocessSchedulerPostApi.get_date_period_overflow(end)
        if start_overflow or end_overflow:
            valid_start = ReprocessSchedulerPostApi.get_valid_period_date(
                start)
            valid_end = ReprocessSchedulerPostApi.get_valid_period_date(end)
            if valid_start == valid_end:
                valid_end += timedelta(seconds=cfg.CONF.collect.period)

            return [str(valid_start), str(valid_end)]

    @staticmethod
    def validate_inputs(
            end_reprocess_time, reason, scope_ids, start_reprocess_time):
        ReprocessSchedulerPostApi.validate_scope_ids(scope_ids)

        if not reason.strip():
            raise http_exceptions.BadRequest(
                "Empty or blank reason text is not allowed. Please, do "
                "inform/register the reason for the reprocessing of a "
                "previously processed timestamp.")
        if end_reprocess_time < start_reprocess_time:
            raise http_exceptions.BadRequest(
                "End reprocessing timestamp [%s] cannot be less than "
                "start reprocessing timestamp [%s]."
                % (start_reprocess_time, end_reprocess_time))

        periods_overflows = ReprocessSchedulerPostApi.get_overflow_from_dates(
            start_reprocess_time, end_reprocess_time)
        if periods_overflows:
            raise http_exceptions.BadRequest(
                "The provided reprocess time window does not comply with "
                "the configured collector period. A valid time window "
                "near the provided one is %s" % periods_overflows)

    @staticmethod
    def validate_scope_ids(scope_ids):
        option_all_selected = False
        for s in scope_ids:
            if s == ALL_SCOPES_OPTION:
                option_all_selected = True
                continue

        if option_all_selected and len(scope_ids) != 1:
            raise http_exceptions.BadRequest(
                "Cannot use 'ALL' with scope ID [%s]. Either schedule a "
                "reprocessing for all active scopes using 'ALL' option, "
                "or inform only the scopes you desire to schedule a "
                "reprocessing." % scope_ids)

    @staticmethod
    def check_if_there_are_invalid_scopes(
            all_scopes_to_reprocess, end_reprocess_time, scope_ids,
            start_reprocess_time):

        invalid_scopes = []
        for s in scope_ids:
            scope_exist_in_db = False
            for scope_to_reprocess in all_scopes_to_reprocess:
                if s == scope_to_reprocess.identifier:
                    scope_exist_in_db = True
                    break

            if not scope_exist_in_db:
                invalid_scopes.append(s)

        if invalid_scopes:
            raise http_exceptions.BadRequest(
                "Scopes %s scheduled to reprocess [start=%s, end=%s] "
                "do not exist."
                % (invalid_scopes, start_reprocess_time, end_reprocess_time))

    @staticmethod
    def validate_start_end_for_reprocessing(all_scopes_to_reprocess,
                                            end_reprocess_time,
                                            start_reprocess_time):

        for scope in all_scopes_to_reprocess:
            last_processed_timestamp = scope.last_processed_timestamp
            if start_reprocess_time > last_processed_timestamp:
                raise http_exceptions.BadRequest(
                    "Cannot execute a reprocessing [start=%s] for scope [%s] "
                    "starting after the last possible timestamp [%s]."
                    % (start_reprocess_time, scope, last_processed_timestamp))
            if end_reprocess_time > scope.last_processed_timestamp:
                raise http_exceptions.BadRequest(
                    "Cannot execute a reprocessing [end=%s] for scope [%s] "
                    "ending after the last possible timestamp [%s]."
                    % (end_reprocess_time, scope, last_processed_timestamp))

    def validate_reprocessing_schedules_overlaps(
            self, all_scopes_to_reprocess, end_reprocess_time,
            start_reprocess_time):

        scheduling_range = DateTimeRange(
            start_reprocess_time, end_reprocess_time)

        for scope_to_reprocess in all_scopes_to_reprocess:
            all_reprocessing_schedules = self.schedule_reprocessing_db.get_all(
                identifier=[scope_to_reprocess.identifier])

            LOG.debug("All schedules [%s] for reprocessing found for scope "
                      "[%s]", all_reprocessing_schedules, scope_to_reprocess)
            if not all_reprocessing_schedules:
                LOG.debug(
                    "No need to validate possible collision of reprocessing "
                    "for scope [%s] because it does not have active "
                    "reprocessing schedules." % scope_to_reprocess)
                continue

            for schedule in all_reprocessing_schedules:
                scheduled_range = DateTimeRange(
                    tzutils.local_to_utc(schedule.start_reprocess_time),
                    tzutils.local_to_utc(schedule.end_reprocess_time))

                try:
                    if scheduling_range.is_intersection(scheduled_range):
                        raise http_exceptions.BadRequest(
                            self.generate_overlap_error_message(
                                scheduled_range, scheduling_range,
                                scope_to_reprocess))
                except ValueError as e:
                    raise http_exceptions.BadRequest(
                        self.generate_overlap_error_message(
                            scheduled_range, scheduling_range,
                            scope_to_reprocess) + "Error: [%s]." % e)

    @staticmethod
    def generate_overlap_error_message(scheduled_range, scheduling_range,
                                       scope_to_reprocess):
        return "Cannot schedule a reprocessing for scope [%s] for " \
               "reprocessing time [%s], because it already has a schedule " \
               "for a similar time range [%s]." % (scope_to_reprocess,
                                                   scheduling_range,
                                                   scheduled_range)


ACCEPTED_GET_REPROCESSING_REQUEST_ORDERS = ['asc', 'desc']


class ReprocessSchedulerGetApi(base.BaseResource):
    def __init__(self, *args, **kwargs):
        super(ReprocessSchedulerGetApi, self).__init__(*args, **kwargs)
        self.schedule_reprocessing_db = storage_state.ReprocessingSchedulerDb()

    @api_utils.paginated
    @api_utils.add_input_schema('query', {
        voluptuous.Optional('scope_ids'): api_utils.MultiQueryParam(str),
        voluptuous.Optional('order', default="desc"):
            api_utils.SingleQueryParam(str)
    })
    @api_utils.add_output_schema({'results': [{
        voluptuous.Required('reason'): validation_utils.get_string_type(),
        voluptuous.Required('scope_id'): validation_utils.get_string_type(),
        voluptuous.Required('start_reprocess_time'):
            validation_utils.get_string_type(),
        voluptuous.Required('end_reprocess_time'):
            validation_utils.get_string_type(),
        voluptuous.Required('current_reprocess_time'):
            validation_utils.get_string_type(),
    }]})
    def get(self, scope_ids=[], path_scope_id=None, offset=0, limit=100,
            order="desc"):
        if path_scope_id and scope_ids:
            LOG.warning("Filtering by scope IDs [%s] and path scope ID [%s] "
                        "does not make sense. You should use only one of "
                        "them. We will use only the path scope ID for this "
                        "request.", scope_ids, path_scope_id)

        if path_scope_id:
            scope_ids = [path_scope_id]

        policy.authorize(
            flask.request.context,
            'schedule:get_task_reprocesses',
            {'tenant_id': flask.request.context.project_id or scope_ids}
        )

        if not isinstance(scope_ids, list):
            scope_ids = [scope_ids]

        # Some versions of python-cloudkittyclient can send the order in upper
        # case, e.g. "DESC". Convert it to lower case for compatibility.
        order = order.lower()

        if order not in ACCEPTED_GET_REPROCESSING_REQUEST_ORDERS:
            raise http_exceptions.BadRequest(
                "The order [%s] is not valid. Accepted values are %s." %
                (order, ACCEPTED_GET_REPROCESSING_REQUEST_ORDERS))

        schedules = self.schedule_reprocessing_db.get_all(
            identifier=scope_ids, remove_finished=False,
            offset=offset, limit=limit, order=order)

        return {
            'results': [{
                'scope_id': s.identifier,
                'reason': s.reason,
                'start_reprocess_time': s.start_reprocess_time.isoformat(),
                'end_reprocess_time': s.end_reprocess_time.isoformat(),
                'current_reprocess_time':
                    s.current_reprocess_time.isoformat() if
                    s.current_reprocess_time else "",
            } for s in schedules]}


class ReprocessesSchedulerGetApi(ReprocessSchedulerGetApi):

    def __init__(self, *args, **kwargs):
        super(ReprocessesSchedulerGetApi, self).__init__(*args, **kwargs)
