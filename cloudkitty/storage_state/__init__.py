# -*- coding: utf-8 -*-
# Copyright 2018 Objectif Libre
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
from oslo_config import cfg
from oslo_db.sqlalchemy import utils
from oslo_log import log
from sqlalchemy import or_ as or_operation
from sqlalchemy import sql

from cloudkitty import db
from cloudkitty.storage_state import migration
from cloudkitty.storage_state import models
from cloudkitty.utils import tz as tzutils


LOG = log.getLogger(__name__)


CONF = cfg.CONF
# NOTE(peschk_l): Required for defaults
CONF.import_opt('backend', 'cloudkitty.fetcher', 'fetcher')
CONF.import_opt('collector', 'cloudkitty.collector', 'collect')
CONF.import_opt('scope_key', 'cloudkitty.collector', 'collect')


def to_list_if_needed(value):
    if not isinstance(value, list):
        value = [value]
    return value


def apply_offset_and_limit(limit, offset, q):
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q


class StateManager(object):
    """Class allowing state management in CloudKitty"""

    model = models.IdentifierState

    def get_all(self,
                identifier=None,
                fetcher=None,
                collector=None,
                scope_key=None,
                active=1,
                limit=100,
                offset=0):
        """Returns the state of all scopes.

        This function returns the state of all scopes with support for optional
        filters.

        :param identifier: optional scope identifiers to filter on
        :type identifier: list
        :param fetcher: optional scope fetchers to filter on
        :type fetcher: list
        :param collector: optional collectors to filter on
        :type collector: list
        :param fetcher: optional fetchers to filter on
        :type fetcher: list
        :param scope_key: optional scope_keys to filter on
        :type scope_key: list
        :param active: optional active to filter scopes by status
                       (active/deactivated)
        :type active: int
        :param limit: optional to restrict the projection
        :type limit: int
        :param offset: optional to shift the projection
        :type offset: int
        """
        with db.session_for_read() as session:

            q = utils.model_query(self.model, session)
            if identifier:
                q = q.filter(
                    self.model.identifier.in_(to_list_if_needed(identifier)))
            if fetcher:
                q = q.filter(
                    self.model.fetcher.in_(to_list_if_needed(fetcher)))
            if collector:
                q = q.filter(
                    self.model.collector.in_(to_list_if_needed(collector)))
            if scope_key:
                q = q.filter(
                    self.model.scope_key.in_(to_list_if_needed(scope_key)))
            if active is not None and active != []:
                q = q.filter(self.model.active.in_(to_list_if_needed(active)))
            q = apply_offset_and_limit(limit, offset, q)

            r = q.all()

        for item in r:
            item.last_processed_timestamp = tzutils.utc_to_local(
                item.last_processed_timestamp)
            item.scope_activation_toggle_date = tzutils.utc_to_local(
                item.scope_activation_toggle_date)
        return r

    def _get_db_item(self, session, identifier,
                     fetcher=None, collector=None, scope_key=None):
        fetcher = fetcher or CONF.fetcher.backend
        collector = collector or CONF.collect.collector
        scope_key = scope_key or CONF.collect.scope_key

        q = utils.model_query(self.model, session)
        r = q.filter(self.model.identifier == identifier). \
            filter(self.model.scope_key == scope_key). \
            filter(self.model.fetcher == fetcher). \
            filter(self.model.collector == collector). \
            first()

        # In case the identifier exists with empty columns, update them
        if not r:
            # NOTE(peschk_l): We must use == instead of 'is' because sqlalchemy
            # overloads this operator
            r = q.filter(self.model.identifier == identifier). \
                filter(self.model.scope_key == None). \
                filter(self.model.fetcher == None). \
                filter(self.model.collector == None). \
                first()  # noqa
            if r:
                r.scope_key = scope_key
                r.collector = collector
                r.fetcher = fetcher
                LOG.info('Updating identifier "{i}" with scope_key "{sk}", '
                         'collector "{c}" and fetcher "{f}"'.format(
                             i=identifier,
                             sk=scope_key,
                             c=collector,
                             f=fetcher))
                session.commit()
        return r

    def set_state(self, identifier, state,
                  fetcher=None, collector=None, scope_key=None):
        """Set the last processed timestamp of a scope.

        This method is deprecated, consider using
        "set_last_processed_timestamp".
        """
        LOG.warning("The method 'set_state' is deprecated. "
                    "Consider using the new method "
                    "'set_last_processed_timestamp'.")
        self.set_last_processed_timestamp(
            identifier, state, fetcher, collector, scope_key)

    def set_last_processed_timestamp(
            self, identifier, last_processed_timestamp, fetcher=None,
            collector=None, scope_key=None):
        """Set the last processed timestamp of a scope.

        If the scope does not exist yet in the database, it will create it.

        :param identifier: Identifier of the scope
        :type identifier: str
        :param last_processed_timestamp: last processed timestamp of the scope
        :type last_processed_timestamp: datetime.datetime
        :param fetcher: Fetcher associated to the scope
        :type fetcher: str
        :param collector: Collector associated to the scope
        :type collector: str
        :param scope_key: scope_key associated to the scope
        :type scope_key: str
        """
        last_processed_timestamp = tzutils.local_to_utc(
            last_processed_timestamp, naive=True)
        with db.session_for_write() as session:
            r = self._get_db_item(
                session, identifier, fetcher, collector, scope_key)

            if r:
                if r.last_processed_timestamp != last_processed_timestamp:
                    r.last_processed_timestamp = last_processed_timestamp
                    session.commit()
            else:
                self.create_scope(identifier, last_processed_timestamp,
                                  fetcher=fetcher, collector=collector,
                                  scope_key=scope_key)

    def create_scope(self, identifier, last_processed_timestamp, fetcher=None,
                     collector=None, scope_key=None, active=True,
                     session=None):
        """Creates a scope in the database.

        :param identifier: Identifier of the scope
        :type identifier: str
        :param last_processed_timestamp: last processed timestamp of the scope
        :type last_processed_timestamp: datetime.datetime
        :param fetcher: Fetcher associated to the scope
        :type fetcher: str
        :param collector: Collector associated to the scope
        :type collector: str
        :param scope_key: scope_key associated to the scope
        :type scope_key: str
        :param active: indicates if the scope is active
        :type active: bool
        :param session: the current database session to be reused
        :type session: object
        """

        with db.session_for_write() as session:

            state_object = self.model(
                identifier=identifier,
                last_processed_timestamp=last_processed_timestamp,
                fetcher=fetcher,
                collector=collector,
                scope_key=scope_key,
                active=active
            )
            session.add(state_object)
            session.commit()

    def get_last_processed_timestamp(self, identifier, fetcher=None,
                                     collector=None, scope_key=None):
        """Get the last processed timestamp of a scope.

        :param identifier: Identifier of the scope
        :type identifier: str
        :param fetcher: Fetcher associated to the scope
        :type fetcher: str
        :param collector: Collector associated to the scope
        :type collector: str
        :param scope_key: scope_key associated to the scope
        :type scope_key: str
        :rtype: datetime.datetime
        """
        with db.session_for_read() as session:
            r = self._get_db_item(
                session, identifier, fetcher, collector, scope_key)
        return tzutils.utc_to_local(r.last_processed_timestamp) if r else None

    def init(self):
        migration.upgrade('head')

    # This is made in order to stay compatible with legacy behavior but
    # shouldn't be used
    def get_tenants(self, begin=None, end=None):
        with db.session_for_read() as session:
            q = utils.model_query(self.model, session)
        return [tenant.identifier for tenant in q]

    def update_storage_scope(self, storage_scope_to_update, scope_key=None,
                             fetcher=None, collector=None, active=None):
        """Update storage scope data.

        :param storage_scope_to_update: The storage scope to update in the DB
        :type storage_scope_to_update: object
        :param fetcher: Fetcher associated to the scope
        :type fetcher: str
        :param collector: Collector associated to the scope
        :type collector: str
        :param scope_key: scope_key associated to the scope
        :type scope_key: str
        :param active: indicates if the storage scope is active for processing
        :type active: bool
        """
        with db.session_for_write() as session:

            db_scope = self._get_db_item(session,
                                         storage_scope_to_update.identifier,
                                         storage_scope_to_update.fetcher,
                                         storage_scope_to_update.collector,
                                         storage_scope_to_update.scope_key)

            if scope_key:
                db_scope.scope_key = scope_key
            if fetcher:
                db_scope.fetcher = fetcher
            if collector:
                db_scope.collector = collector
            if active is not None and active != db_scope.active:
                db_scope.active = active

                now = tzutils.localized_now()
                db_scope.scope_activation_toggle_date = tzutils.local_to_utc(
                    now, naive=True)

            session.commit()

    def is_storage_scope_active(self, identifier, fetcher=None,
                                collector=None, scope_key=None):
        """Checks if a storage scope is active

        :param identifier: Identifier of the scope
        :type identifier: str
        :param fetcher: Fetcher associated to the scope
        :type fetcher: str
        :param collector: Collector associated to the scope
        :type collector: str
        :param scope_key: scope_key associated to the scope
        :type scope_key: str
        :rtype: datetime.datetime
        """
        with db.session_for_read() as session:
            r = self._get_db_item(
                session, identifier, fetcher, collector, scope_key)

        return r.active


class ReprocessingSchedulerDb(object):
    """Class to access and operator the reprocessing scheduler in the DB"""

    model = models.ReprocessingScheduler

    def get_all(self, identifier=None, remove_finished=True,
                limit=100, offset=0, order="desc"):
        """Returns all schedules for reprocessing for a given resource

        :param identifier: Identifiers of the scopes
        :type identifier: str
        :param remove_finished: option to remove from the projection the
                                reprocessing scheduled that already finished.
        :type remove_finished: bool
        :param limit: optional to restrict the projection
        :type limit: int
        :param offset: optional to shift the projection
        :type offset: int
        :param order: optional parameter to indicate the order of the
                      projection. The ordering field will be the `id`.
        :type order: str
        """
        with db.session_for_read() as session:

            query = utils.model_query(self.model, session)

            if identifier:
                query = query.filter(self.model.identifier.in_(identifier))
            if remove_finished:
                query = self.remove_finished_processing_schedules(query)
            if order:
                query = query.order_by(sql.text("id %s" % order))

            query = apply_offset_and_limit(limit, offset, query)

            result_set = query.all()

        return result_set

    def remove_finished_processing_schedules(self, query):
        return query.filter(or_operation(
            self.model.current_reprocess_time.is_(None),
            self.model.current_reprocess_time < self.model.end_reprocess_time
        ))

    def persist(self, reprocessing_scheduler):
        """Persists the reprocessing_schedule

        :param reprocessing_scheduler: reprocessing schedule that we want to
                                       persist in the database.
        :type reprocessing_scheduler: models.ReprocessingScheduler
        """

        with db.session_for_write() as session:

            session.add(reprocessing_scheduler)
            session.commit()

    def get_from_db(self, identifier=None, start_reprocess_time=None,
                    end_reprocess_time=None):
        """Get the reprocessing schedule from DB

        :param identifier: Identifier of the scope
        :type identifier: str
        :param start_reprocess_time: the start time used in the
                                     reprocessing schedule
        :type start_reprocess_time: datetime.datetime
        :param end_reprocess_time: the end time used in the
                                     reprocessing schedule
        :type end_reprocess_time: datetime.datetime
        """
        with db.session_for_read() as session:

            result_set = self._get_db_item(
                end_reprocess_time, identifier, session, start_reprocess_time)

        return result_set

    def _get_db_item(self, end_reprocess_time, identifier, session,
                     start_reprocess_time):

        query = utils.model_query(self.model, session)
        query = query.filter(self.model.identifier == identifier)
        query = query.filter(
            self.model.start_reprocess_time == start_reprocess_time)
        query = query.filter(
            self.model.end_reprocess_time == end_reprocess_time)
        query = self.remove_finished_processing_schedules(query)

        return query.first()

    def update_reprocessing_time(self, identifier=None,
                                 start_reprocess_time=None,
                                 end_reprocess_time=None,
                                 new_current_time_stamp=None):
        """Update current processing time for a reprocessing schedule

        :param identifier: Identifier of the scope
        :type identifier: str
        :param start_reprocess_time: the start time used in the
                                     reprocessing schedule
        :type start_reprocess_time: datetime.datetime
        :param end_reprocess_time: the end time used in the
                                     reprocessing schedule
        :type end_reprocess_time: datetime.datetime
        :param new_current_time_stamp: the new current timestamp to set
        :type new_current_time_stamp: datetime.datetime
        """

        with db.session_for_write() as session:

            result_set = self._get_db_item(
                end_reprocess_time, identifier, session, start_reprocess_time)

            if not result_set:
                LOG.warning("Trying to update current time to [%s] for "
                            "identifier [%s] and reprocessing range [start=%, "
                            "end=%s], but we could not find a this task in the"
                            " database.",
                            new_current_time_stamp, identifier,
                            start_reprocess_time, end_reprocess_time)
                return
            new_current_time_stamp = tzutils.local_to_utc(
                new_current_time_stamp, naive=True)

            result_set.current_reprocess_time = new_current_time_stamp
            session.commit()
