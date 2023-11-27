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
import abc
import datetime

from oslo_log import log as logging

from oslo_config import cfg

from cloudkitty import storage_state

from werkzeug import exceptions as http_exceptions


storage_opts = [
    cfg.IntOpt(
        'retention_period',
        default=2400,
        help='Duration after which data should be cleaned up/aggregated. '
        'Duration is given in hours. Defaults to 2400 (100 days)'
    ),
]

CONF = cfg.CONF
CONF.register_opts(storage_opts, 'storage')

LOG = logging.getLogger(__name__)


class BaseStorage(object, metaclass=abc.ABCMeta):
    """Abstract class for v2 storage objects."""

    def __init__(self, *args, **kwargs):
        """Left empty so that child classes don't need to implement this."""

    @abc.abstractmethod
    def init(self):
        """Called for storage backend initialization"""

    # NOTE(peschk_l): scope_id must not be used by any v2 storage backend. It
    # is only present for backward compatibility with the v1 storage. It will
    # be removed together with the v1 storage
    @abc.abstractmethod
    def push(self, dataframes, scope_id=None):
        """Pushes dataframes to the storage backend

        :param dataframes: List of dataframes
        :type dataframes: [cloudkitty.dataframe.DataFrame]
        """

    @abc.abstractmethod
    def retrieve(self, begin=None, end=None,
                 filters=None,
                 metric_types=None,
                 offset=0, limit=1000, paginate=True):
        """Returns the following dict::

            {
               'total': int, # total amount of measures found
               'dataframes': list of dataframes,
            }

        :param begin: Start date
        :type begin: datetime
        :param end: End date
        :type end: datetime
        :param filters: Attributes to filter on. ex: {'flavor_id': '42'}
        :type filters: dict
        :param metric_types: Metric type to filter on.
        :type metric_types: str or list
        :param offset: Offset for pagination
        :type offset: int
        :param limit: Maximum amount of elements to return
        :type limit: int
        :param paginate: Defaults to True. If False, all found results
                         will be returned.
        :type paginate: bool
        :rtype: dict
       """

    @abc.abstractmethod
    def delete(self, begin=None, end=None, filters=None):
        """Deletes all data from for the given period and filters.

        :param begin: Start date
        :type begin: datetime
        :param end: End date
        :type end: datetime
        :param filters: Attributes to filter on. ex: {'flavor_id': '42'}
        :type filters: dict
        """

    @abc.abstractmethod
    def total(self, groupby=None, begin=None, end=None, metric_types=None,
              filters=None, custom_fields=None, offset=0, limit=1000,
              paginate=True):
        """Returns a grouped total for given groupby.

        :param groupby: Attributes on which to group by. These attributes must
                        be part of the 'groupby' section for the given metric
                        type in metrics.yml. In order to group by metric type,
                        add 'type' to the groupby list.
        :type groupby: list of strings
        :param begin: Start date
        :type begin: datetime
        :param end: End date
        :type end: datetime
        :param metric_types: Metric type to filter on.
        :type metric_types: str or list
        :param custom_fields: the custom fields that one desires to add in
                              the summary reporting. Each driver must handle
                              these values by themselves.
        :type: custom_fields: list of strings
        :param filters: Attributes to filter on. ex: {'flavor_id': '42'}
        :type filters: dict
        :param offset: Offset for pagination
        :type offset: int
        :param limit: Maximum amount of elements to return
        :type limit: int
        :param paginate: Defaults to True. If False, all found results
                         will be returned.
        :type paginate: bool

        :rtype: dict

        Returns a dict with the following format::

            {
               'total': int, # total amount of results found
               'results': list of results,
            }

        Each result has the following format::

            {
                'begin': XXX,
                'end': XXX,
                'rate': XXX,
                'groupby1': XXX,
                'groupby2': XXX
            }
        """

    @staticmethod
    def get_retention():
        """Returns the retention period defined in the configuration.

        :rtype: datetime.timedelta
        """
        return datetime.timedelta(hours=CONF.storage.retention_period)

    # NOTE(lpeschke): This is only kept for v1 storage backward compatibility
    def get_tenants(self, begin=None, end=None):
        return storage_state.StateManager().get_tenants(begin, end)

    TIME_COMMANDS_MAP = {"d": "day_of_the_year", "w": "week_of_the_year",
                         "m": "month", "y": "year"}

    def parse_groupby_syntax_to_groupby_elements(self, groupbys):
        if not groupbys:
            LOG.debug("No groupby to process syntax.")
            return groupbys

        groupbys_parsed = []
        for elem in groupbys:
            if 'time' in elem:
                time_command = elem.split('-')
                number_of_parts = len(time_command)
                if number_of_parts == 2:
                    g = self.TIME_COMMANDS_MAP.get(time_command[1])
                    if not g:
                        raise http_exceptions.BadRequest(
                            "Invalid groupby time option. There is no "
                            "groupby processing for [%s]." % elem)

                    LOG.debug("Replacing API groupby time command [%s] with "
                              "internal groupby command [%s].", elem, g)
                    elem = g

                elif number_of_parts > 2:
                    LOG.warning("The groupby [%s] command is not expected for "
                                "storage backend [%s]. Therefore, we leave it "
                                "as is.", elem, self)

            groupbys_parsed.append(elem)
        return groupbys_parsed
