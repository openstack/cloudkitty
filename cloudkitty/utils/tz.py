# Copyright 2019 Objectif Libre
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
"""
Timezone-related utilities
"""
import calendar
import datetime

from dateutil import tz
from oslo_utils import timeutils


_LOCAL_TZ = tz.tzlocal()


def localized_now():
    """Returns a datetime object with timezone information."""
    return datetime.datetime.now().replace(tzinfo=_LOCAL_TZ, microsecond=0)


def local_to_utc(dt, naive=False):
    """Converts a localized datetime object to UTC.

    If no tz info is provided, the object will be considered as being already
    in UTC, and the timezone will be set to UTC.

    :param dt: object to convert
    :type dt: datetime.datetime
    :param naive: If True, remove timezone information from the final object.
                  Defaults to False.
    :type naive: bool
    :rtype: datetime.datetime
    """
    # NOTE(peschk_l): In python2, astimezone() raises a ValueError if it is
    # applied to a naive datetime object. In python3 however, the naive object
    # is considered as being in the system's time.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())

    output = dt.astimezone(tz.tzutc())
    if naive:
        output = output.replace(tzinfo=None)
    return output


def utc_to_local(dt):
    """Converts an UTC datetime object to a localized datetime object.

    If no tz info is provided, the object will be considered as being UTC.

    :param dt: object to convert
    :type dt: datetime.datetime
    :rtype: datetime.datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())
    return dt.astimezone(_LOCAL_TZ)


def dt_from_iso(time_str, as_utc=False):
    """Parses a timezone-aware datetime object from an iso8601 str.

    Returns the object as being from the local timezone.

    :param time_str: string to parse
    :type time_str: str
    :param as_utc: Return the datetime object as being from the UTC timezone
    :type as_utc: bool
    :rtype: datetime.datetime
    """
    return timeutils.parse_isotime(time_str).astimezone(
        tz.tzutc() if as_utc else _LOCAL_TZ).replace(microsecond=0)


def dt_from_ts(ts, as_utc=False):
    """Parses a timezone-aware datetime object from an epoch timestamp.

    Returns the object as being from the local timezone.
    """
    return datetime.datetime.fromtimestamp(
        ts, tz.tzutc() if as_utc else _LOCAL_TZ)


def add_delta(dt, delta):
    """Adds a timedelta to a datetime object.

    This is done by transforming the object to a naive UTC object, adding the
    timedelta and transforming it back to a localized object. This helps to
    avoid cases like this when transiting from winter to summertime:

    >>> dt, delta
    (datetime.datetime(2019, 3, 31, 0, 0, tzinfo=tzlocal()),
     datetime.timedelta(0, 3600))
    >>> dt += delta
    >>> dt.isoformat()
    '2019-03-31T01:00:00+01:00'
    >>> dt += delta
    >>> dt.isoformat()
    '2019-03-31T02:00:00+02:00' # This is the same time as the previous one
    """
    return utc_to_local(local_to_utc(dt, naive=True) + delta)


def substract_delta(dt, delta):
    """Substracts a timedelta from a datetime object."""
    return utc_to_local(local_to_utc(dt, naive=True) - delta)


def get_month_start(dt=None, naive=False):
    """Returns the start of the month in the local timezone.

    If no parameter is provided, returns the start of the current month. If
    the provided parameter is naive, it will be considered as UTC and tzinfo
    will be added, except if naive is True.

    :param dt: Month to return the begin of.
    :type dt: datetime.datetime
    :param naive: If True, remove timezone information from the final object.
                  Defaults to False.
    :type naive: bool
    :rtype: datetime.datetime
    """
    if not dt:
        dt = localized_now()
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=tz.tzutc()).astimezone(_LOCAL_TZ)
    if naive:
        dt = local_to_utc(dt, naive=True)
    return datetime.datetime(dt.year, dt.month, 1, tzinfo=dt.tzinfo)


def get_next_month(dt=None, naive=False):
    """Returns the start of the next month in the local timezone.

    If no parameter is provided, returns the start of the next month. If
    the provided parameter is naive, it will be considered as UTC.

    :param dt: Datetime to return the next month of.
    :type dt: datetime.datetime
    :param naive: If True, remove timezone information from the final object.
                  Defaults to False.
    :type naive: bool
    :rtype: datetime.datetime
    """
    start = get_month_start(dt, naive=naive)
    month_days = calendar.monthrange(start.year, start.month)[1]
    return add_delta(start, datetime.timedelta(days=month_days))


def diff_seconds(one, two):
    """Returns the difference in seconds between two datetime objects.

    Objects will be converted to naive UTC objects before calculating the
    difference. The return value is the absolute value of the difference.

    :param one: First datetime object
    :type one: datetime.datetime
    :param two: datetime object to substract from the first one
    :type two: datetime.datetime
    :rtype: int
    """
    return abs(int((local_to_utc(one, naive=True)
                    - local_to_utc(two, naive=True)).total_seconds()))
