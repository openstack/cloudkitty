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
import re
from unittest import mock

from datetimerange import DateTimeRange
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2.task import reprocess
from cloudkitty import tests
from cloudkitty.utils import tz as tzutils


class TestReprocessSchedulerPostApi(tests.TestCase):

    def setUp(self):
        super(TestReprocessSchedulerPostApi, self).setUp()
        self.endpoint = reprocess.ReprocessSchedulerPostApi()
        self.scope_ids = ["some-other-scope-id",
                          "5e56cb64-4980-4466-9fce-d0133c0c221e"]

        self.start_reprocess_time = self.endpoint.get_valid_period_date(
            tzutils.localized_now())
        self.end_reprocess_time = self.endpoint.get_valid_period_date(
            self.start_reprocess_time + datetime.timedelta(hours=1))

        self.reason = "We are testing the reprocess API."

    def test_validate_scope_ids_all_option_with_scope_ids(self):
        self.scope_ids.append('ALL')

        expected_message = \
            "400 Bad Request: Cannot use 'ALL' with scope ID [['some-other-" \
            "scope-id', '5e56cb64-4980-4466-9fce-d0133c0c221e', 'ALL']]. " \
            "Either schedule a reprocessing for all active scopes using " \
            "'ALL' option, or inform only the scopes you desire to schedule " \
            "a reprocessing."
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(http_exceptions.BadRequest, expected_message,
                               self.endpoint.validate_scope_ids,
                               self.scope_ids)

        self.scope_ids.remove('ALL')
        self.endpoint.validate_scope_ids(self.scope_ids)

    def test_validate_inputs_blank_reason(self):

        expected_message = \
            "400 Bad Request: Empty or blank reason text is not allowed. " \
            "Please, do inform/register the reason for the reprocessing of " \
            "a previously processed timestamp."
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(http_exceptions.BadRequest, expected_message,
                               self.endpoint.validate_inputs,
                               self.end_reprocess_time, "", self.scope_ids,
                               self.start_reprocess_time)

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.endpoint.validate_inputs, self.end_reprocess_time,
            "  ", self.scope_ids, self.start_reprocess_time)

        self.endpoint.validate_inputs(
            self.end_reprocess_time, self.reason, self.scope_ids,
            self.start_reprocess_time)

    def test_validate_inputs_end_date_less_than_start_date(self):
        original_end_reprocess_time = self.end_reprocess_time

        self.end_reprocess_time =\
            self.start_reprocess_time - datetime.timedelta(hours=1)

        expected_message = \
            "400 Bad Request: End reprocessing timestamp [%s] cannot be " \
            "less than start reprocessing timestamp [%s]." % (
                self.start_reprocess_time, self.end_reprocess_time)

        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(http_exceptions.BadRequest, expected_message,
                               self.endpoint.validate_inputs,
                               self.end_reprocess_time, self.reason,
                               self.scope_ids, self.start_reprocess_time)

        self.end_reprocess_time = original_end_reprocess_time
        self.endpoint.validate_inputs(
            self.end_reprocess_time, self.reason, self.scope_ids,
            self.start_reprocess_time)

    def test_validate_inputs_different_from_configured_period(self):
        original_end_reprocess_time = self.end_reprocess_time

        self.end_reprocess_time += datetime.timedelta(seconds=1)

        expected_message = "400 Bad Request: The provided reprocess time " \
                           "window does not comply with the configured" \
                           " collector period. A valid time window near " \
                           "the provided one is ['%s', '%s']" % (
                               self.start_reprocess_time,
                               original_end_reprocess_time)

        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(http_exceptions.BadRequest, expected_message,
                               self.endpoint.validate_inputs,
                               self.end_reprocess_time, self.reason,
                               self.scope_ids, self.start_reprocess_time)

        self.end_reprocess_time = original_end_reprocess_time
        self.endpoint.validate_inputs(
            self.end_reprocess_time, self.reason, self.scope_ids,
            self.start_reprocess_time)

    def test_validate_time_window_smaller_than_configured_period(self):
        start = datetime.datetime(year=2022, day=22, month=2, hour=10,
                                  minute=10, tzinfo=tzutils._LOCAL_TZ)
        end = datetime.datetime(year=2022, day=22, month=2, hour=10,
                                minute=20, tzinfo=tzutils._LOCAL_TZ)
        expected_start = datetime.datetime(year=2022, day=22, month=2, hour=10,
                                           tzinfo=tzutils._LOCAL_TZ)
        expected_end = datetime.datetime(year=2022, day=22, month=2, hour=11,
                                         tzinfo=tzutils._LOCAL_TZ)

        expected_message = "400 Bad Request: The provided reprocess time " \
                           "window does not comply with the configured" \
                           " collector period. A valid time window near " \
                           "the provided one is ['%s', '%s']" % (
                               expected_start,
                               expected_end)

        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(http_exceptions.BadRequest, expected_message,
                               self.endpoint.validate_inputs,
                               end, self.reason,
                               self.scope_ids, start)

    def test_check_if_there_are_invalid_scopes(self):
        all_scopes = self.generate_all_scopes_object()

        element_removed = all_scopes.pop(0)

        expected_message = \
            "400 Bad Request: Scopes [\'%s\'] scheduled to reprocess "\
            "[start=%s, end=%s] do not exist."\
            % (element_removed.identifier, self.start_reprocess_time,
               self.end_reprocess_time)

        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.endpoint.check_if_there_are_invalid_scopes, all_scopes,
            self.end_reprocess_time, self.scope_ids, self.start_reprocess_time)

        all_scopes.append(element_removed)
        self.endpoint.check_if_there_are_invalid_scopes(
            all_scopes, self.end_reprocess_time, self.scope_ids,
            self.start_reprocess_time)

    def generate_all_scopes_object(self, last_processed_time=None):
        all_scopes = []

        def mock_to_string(self):
            return "toStringMock"

        for s in self.scope_ids:
            scope = mock.Mock()
            scope.identifier = s
            scope.last_processed_timestamp = last_processed_time
            scope.__str__ = mock_to_string
            all_scopes.append(scope)
        return all_scopes

    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.get_all")
    def test_validate_reprocessing_schedules_overlaps(
            self, schedule_get_all_mock):

        self.configure_and_execute_overlap_test(schedule_get_all_mock,
                                                self.start_reprocess_time,
                                                self.end_reprocess_time)

        self.configure_and_execute_overlap_test(schedule_get_all_mock,
                                                self.end_reprocess_time,
                                                self.start_reprocess_time)

        end_reprocess_time =\
            self.end_reprocess_time + datetime.timedelta(hours=5)

        self.configure_and_execute_overlap_test(schedule_get_all_mock,
                                                self.start_reprocess_time,
                                                end_reprocess_time)

        start_reprocess_time =\
            self.start_reprocess_time + datetime.timedelta(hours=1)

        self.configure_and_execute_overlap_test(schedule_get_all_mock,
                                                start_reprocess_time,
                                                end_reprocess_time)

        start_reprocess_time =\
            self.start_reprocess_time - datetime.timedelta(hours=1)

        self.configure_and_execute_overlap_test(schedule_get_all_mock,
                                                start_reprocess_time,
                                                end_reprocess_time)

        start_reprocess_time =\
            self.end_reprocess_time + datetime.timedelta(hours=1)

        self.configure_schedules_mock(schedule_get_all_mock,
                                      start_reprocess_time,
                                      end_reprocess_time)

        self.endpoint.validate_reprocessing_schedules_overlaps(
            self.generate_all_scopes_object(), self.end_reprocess_time,
            self.start_reprocess_time)

        schedule_get_all_mock.assert_has_calls([
            mock.call(identifier=[self.scope_ids[0]]),
            mock.call(identifier=[self.scope_ids[1]])])

    def configure_and_execute_overlap_test(self, schedule_get_all_mock,
                                           start_reprocess_time,
                                           end_reprocess_time):

        self.configure_schedules_mock(
            schedule_get_all_mock, start_reprocess_time, end_reprocess_time)

        scheduling_range = DateTimeRange(
            tzutils.utc_to_local(self.start_reprocess_time),
            tzutils.utc_to_local(self.end_reprocess_time))
        scheduled_range = DateTimeRange(
            tzutils.local_to_utc(start_reprocess_time),
            tzutils.local_to_utc(end_reprocess_time))
        expected_message = \
            "400 Bad Request: Cannot schedule a reprocessing for scope " \
            "[toStringMock] for reprocessing time [%s], because it already " \
            "has a schedule for a similar time range [%s]." \
            % (scheduling_range, scheduled_range)

        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.endpoint.validate_reprocessing_schedules_overlaps,
            self.generate_all_scopes_object(),
            self.end_reprocess_time, self.start_reprocess_time)

        schedule_get_all_mock.assert_called_with(
            identifier=[self.scope_ids[0]])

    def configure_schedules_mock(self, schedule_get_all_mock,
                                 start_reprocess_time, end_reprocess_time):
        schedules = []
        schedule_get_all_mock.return_value = schedules
        all_scopes = self.generate_all_scopes_object()
        for s in all_scopes:
            schedule_mock = mock.Mock()
            schedule_mock.identifier = s.identifier
            schedule_mock.start_reprocess_time = start_reprocess_time
            schedule_mock.end_reprocess_time = end_reprocess_time
            schedules.append(schedule_mock)

    def test_validate_start_end_for_reprocessing(self):
        all_scopes = self.generate_all_scopes_object(
            last_processed_time=self.start_reprocess_time)

        base_error_message = "400 Bad Request: Cannot execute a " \
                             "reprocessing [%s=%s] for scope [toStringMock] " \
                             "%s after the last possible timestamp [%s]."

        start_reprocess_time =\
            self.start_reprocess_time + datetime.timedelta(hours=1)

        expected_message = base_error_message % ("start",
                                                 start_reprocess_time,
                                                 "starting",
                                                 self.start_reprocess_time)
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.endpoint.validate_start_end_for_reprocessing, all_scopes,
            self.end_reprocess_time, start_reprocess_time)

        all_scopes = self.generate_all_scopes_object(
            last_processed_time=self.end_reprocess_time)

        end_processing_time =\
            self.end_reprocess_time + datetime.timedelta(hours=1)

        expected_message = base_error_message % ("end",
                                                 end_processing_time,
                                                 "ending",
                                                 self.end_reprocess_time)
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.endpoint.validate_start_end_for_reprocessing, all_scopes,
            end_processing_time, self.start_reprocess_time)

        self.endpoint.validate_start_end_for_reprocessing(
            all_scopes, self.end_reprocess_time,
            self.start_reprocess_time)

        all_scopes = self.generate_all_scopes_object(
            last_processed_time=self.start_reprocess_time)

        self.endpoint.validate_start_end_for_reprocessing(
            all_scopes, self.start_reprocess_time,
            self.start_reprocess_time)

    @mock.patch("flask.request")
    @mock.patch("cloudkitty.common.policy.authorize")
    @mock.patch("cloudkitty.api.v2.task.reprocess"
                ".ReprocessSchedulerPostApi.validate_inputs")
    @mock.patch("cloudkitty.api.v2.task.reprocess"
                ".ReprocessSchedulerPostApi"
                ".check_if_there_are_invalid_scopes")
    @mock.patch("cloudkitty.api.v2.task.reprocess."
                "ReprocessSchedulerPostApi."
                "validate_start_end_for_reprocessing")
    @mock.patch("cloudkitty.api.v2.task.reprocess"
                ".ReprocessSchedulerPostApi"
                ".validate_reprocessing_schedules_overlaps")
    @mock.patch("cloudkitty.storage_state.StateManager.get_all")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.persist")
    def test_post(self, reprocessing_scheduler_db_persist_mock,
                  state_manager_get_all_mock,
                  validate_reprocessing_schedules_overlaps_mock,
                  validate_start_end_for_reprocessing_mock,
                  check_if_there_are_invalid_scopes_mock, validate_inputs_mock,
                  policy_mock, request_mock):

        state_manager_get_all_mock.return_value =\
            self.generate_all_scopes_object()

        request_mock.context = mock.Mock()
        request_mock.context.project_id = "project_id_mock"

        def get_json_mock():
            return {"scope_ids": self.scope_ids[0],
                    "start_reprocess_time": str(self.start_reprocess_time),
                    "end_reprocess_time":  str(self.end_reprocess_time),
                    "reason": self.reason}

        request_mock.get_json = get_json_mock

        self.endpoint.post()

        self.assertEqual(reprocessing_scheduler_db_persist_mock.call_count, 2)
        state_manager_get_all_mock.assert_called_once()
        validate_reprocessing_schedules_overlaps_mock.assert_called_once()
        validate_start_end_for_reprocessing_mock.assert_called_once()
        check_if_there_are_invalid_scopes_mock.assert_called_once()
        validate_inputs_mock.assert_called_once()
        policy_mock.assert_called_once()


class TestReprocessingSchedulerGetApi(tests.TestCase):

    def setUp(self):
        super(TestReprocessingSchedulerGetApi, self).setUp()
        self.endpoint = reprocess.ReprocessSchedulerGetApi()

    @mock.patch("flask.request")
    @mock.patch("cloudkitty.common.policy.authorize")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.get_all")
    def test_get(self, reprocessing_db_get_all_mock,
                 policy_mock, request_mock):

        time_now = tzutils.localized_now()
        schedule_mock = mock.Mock()
        schedule_mock.id = 1
        schedule_mock.identifier = "scope_identifier"
        schedule_mock.reason = "reason to process"
        schedule_mock.current_reprocess_time = time_now
        schedule_mock.start_reprocess_time =\
            time_now - datetime.timedelta(hours=10)

        schedule_mock.end_reprocess_time =\
            time_now + datetime.timedelta(hours=10)

        reprocessing_db_get_all_mock.return_value = [schedule_mock]
        request_mock.context = mock.Mock()
        request_mock.args = mock.Mock()
        request_mock.args.lists = mock.Mock()
        request_mock.args.lists.return_value = []
        list_all_return = self.endpoint.get()

        self.assertTrue("results" in list_all_return)
        self.assertTrue("id" not in list_all_return['results'][0])
        self.assertTrue("scope_id" in list_all_return['results'][0])
        self.assertTrue("reason" in list_all_return['results'][0])
        self.assertTrue(
            "current_reprocess_time" in list_all_return['results'][0])
        self.assertTrue(
            "start_reprocess_time" in list_all_return['results'][0])
        self.assertTrue(
            "end_reprocess_time" in list_all_return['results'][0])

        self.assertEqual("scope_identifier",
                         list_all_return['results'][0]['scope_id'])
        self.assertEqual("reason to process",
                         list_all_return['results'][0]['reason'])
        self.assertEqual(time_now.isoformat(), list_all_return['results'][0][
            'current_reprocess_time'])
        self.assertEqual((time_now - datetime.timedelta(hours=10)).isoformat(),
                         list_all_return['results'][0]['start_reprocess_time'])
        self.assertEqual((time_now + datetime.timedelta(hours=10)).isoformat(),
                         list_all_return['results'][0]['end_reprocess_time'])

        reprocessing_db_get_all_mock.assert_called_once()
        policy_mock.assert_called_once()
