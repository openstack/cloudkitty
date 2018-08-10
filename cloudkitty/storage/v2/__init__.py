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
# @author: Luka Peschke
#
import abc
import datetime

from oslo_config import cfg
import six

from cloudkitty import storage_state


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


@six.add_metaclass(abc.ABCMeta)
class BaseStorage(object):
    """Abstract class for v2 storage objects."""

    def __init__(self, *args, **kwargs):
        """Left empty so that child classes don't need to implement this."""

    @abc.abstractmethod
    def init(self):
        """Called for storage backend initialization"""

    @abc.abstractmethod
    def push(self, dataframes, scope_id):
        """Pushes dataframes to the storage backend

        A dataframe has the following format::

            {
                "usage": {
                    "bananas": [ # metric name
                        {
                            "vol": {
                                "unit": "banana",
                                "qty": 1
                            },
                            "rating": {
                                "price": 1
                            },
                            "groupby": {
                                "xxx_id": "hello",
                                "yyy_id": "bye",
                            },
                            "metadata": {
                                "flavor": "chocolate",
                                "eaten_by": "gorilla",
                            },
                       }
                    ],
                    "metric_name2": [...],
                }
               "period": {
                    "begin": "1239781290", # timestamp
                    "end": "1239793490", # timestamp
                }
            }

        :param dataframes: List of dataframes
        :type dataframes: list
        :param scope_id: ID of the scope (A project ID for example).
        :type scope_id: str
        """

    @abc.abstractmethod
    def retrieve(self, begin=None, end=None,
                 filters=None, group_filters=None,
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
        :param filters: Metadata to filter on. ex: {'flavor_id': '42'}
        :type filters: dict
        :param group_filters: Groupby to filter on. ex: {'project_id': '123ab'}
        :type group_filters: dict
        :param metric_types: Metric type to filter on.
        :type metric_types: str or list
        :param offset: Offset for pagination
        :type offset: int
        :param limit: Maximum amount of elements to return
        :type limit: int
        :param paginate: Defaults to True. If False, all found results
                         will be returned.
        :type limit: int
        :rtype: dict
       """

    @abc.abstractmethod
    def total(self, groupby=None,
              begin=None, end=None,
              metric_types=None,
              filters=None, group_filters=None):
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
        :param filters: Metadata to filter on. ex: {'flavor_id': '42'}
        :type filters: dict
        :param group_filters: Groupby to filter on. ex: {'project_id': '123ab'}
        :type group_filters: dict
        :param metric_types: Metric type to filter on.
        :type metric_types: str or list
        :rtype: list of dicts

        returns a list of dicts with the following format::

            {
                'begin': XXX,
                'end': XXX,
                'type': XXX,
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
