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
import collections
import datetime
import decimal
import functools

import voluptuous
from werkzeug import datastructures

from cloudkitty.utils import json
from cloudkitty.utils import tz as tzutils
from cloudkitty.utils import validation as vutils

# NOTE(peschk_l): qty and price are converted to strings to avoid
# floating-point conversion issues:
# Decimal(0.121) == Decimal('0.12099999999999999644728632119')
# Decimal(str(0.121)) == Decimal('0.121')
DATAPOINT_SCHEMA = voluptuous.Schema({
    voluptuous.Required('vol'): {
        voluptuous.Required('unit'): vutils.get_string_type(),
        voluptuous.Required('qty'): voluptuous.Coerce(str),
    },
    voluptuous.Required('rating', default={}): {
        voluptuous.Required('price', default=0):
        voluptuous.Coerce(str),
    },
    voluptuous.Required('groupby'): voluptuous.Coerce(dict),
    voluptuous.Required('metadata'): voluptuous.Coerce(dict),
})


_DataPointBase = collections.namedtuple(
    "DataPoint",
    field_names=("unit", "qty", "price", "groupby", "metadata", "description"))


class DataPoint(_DataPointBase):

    def __new__(cls, unit, qty, price, groupby, metadata, description=None):
        return _DataPointBase.__new__(
            cls,
            unit or "undefined",
            # NOTE(peschk_l): avoids floating-point issues.
            decimal.Decimal(str(qty) if isinstance(qty, float) else qty),
            decimal.Decimal(str(price) if isinstance(price, float) else price),
            datastructures.ImmutableDict(groupby),
            datastructures.ImmutableDict(metadata),
            description
        )

    def set_price(self, price):
        """Sets the price of the DataPoint and returns a new object."""
        return self._replace(price=price)

    def as_dict(self, legacy=False, mutable=False):
        """Returns a dict representation of the object.

        The returned dict is immutable by default and has the
        following format::
           {
               "vol": {
                   "unit": "GiB",
                   "qty": 1.2,
               },
               "rating": {
                   "price": 0.04,
               },
               "groupby": {
                   "group_one": "one",
                   "group_two": "two",
               },
               "metadata": {
                   "attr_one": "one",
                   "attr_two": "two",
                },
           }

        The dict can also be returned in the legacy (v1 storage) format. In
        that case, `groupby` and `metadata` will be removed and merged together
        into the `desc` key.

        :param legacy: Defaults to False. If True, returned dict is in legacy
                       format.
        :type legacy: bool
        :param mutable: Defaults to False. If True, returns a normal dict
                        instead of an ImmutableDict.
        :type mutable: bool
        """
        output = {
            "vol": {
                "unit": self.unit,
                "qty": self.qty,
            },
            "rating": {
                "price": self.price,
            },
            "groupby": dict(self.groupby) if mutable else self.groupby,
            "metadata": dict(self.metadata) if mutable else self.metadata,
        }
        if legacy:
            desc = output.pop("metadata")
            desc.update(output.pop("groupby"))
            output['desc'] = desc

        return output if mutable else datastructures.ImmutableDict(output)

    def json(self, legacy=False):
        """Returns a json representation of the dict returned by `as_dict`.

        :param legacy: Defaults to False. If True, returned dict is in legacy
                       format.
        :type legacy: bool
        :rtype: str
        """
        return json.dumps(self.as_dict(legacy=legacy, mutable=True))

    @classmethod
    def from_dict(cls, dict_, legacy=False):
        """Returns a new DataPoint instance build from a dict.

        :param dict_: Dict to build the DataPoint from
        :type dict_: dict
        :param legacy: Set to true to convert the dict to a the new format
                       before validating it.
        :rtype: DataPoint
        """
        try:
            if legacy:
                dict_['groupby'] = dict_.pop('desc')
                dict_['metadata'] = {}
            valid = DATAPOINT_SCHEMA(dict_)
            return cls(
                unit=valid["vol"]["unit"],
                qty=valid["vol"]["qty"],
                price=valid["rating"]["price"],
                groupby=valid["groupby"],
                metadata=valid["metadata"],
            )
        except (voluptuous.Invalid, KeyError) as e:
            raise ValueError("{} isn't a valid DataPoint: {}".format(dict_, e))

    @property
    def desc(self):
        output = dict(self.metadata)
        output.update(self.groupby)
        return datastructures.ImmutableDict(output)


DATAFRAME_SCHEMA = voluptuous.Schema({
    voluptuous.Required('period'): {
        voluptuous.Required('begin'): voluptuous.Any(
            datetime.datetime, tzutils.dt_from_iso),
        voluptuous.Required('end'): voluptuous.Any(
            datetime.datetime, tzutils.dt_from_iso),
    },
    voluptuous.Required('usage'): vutils.IterableValuesDict(
        str, DataPoint.from_dict),
})


class DataFrame(object):

    __slots__ = ("start", "end", "_usage")

    def __init__(self, start, end, usage=None):
        if not isinstance(start, datetime.datetime):
            raise TypeError(
                '"start" must be of type datetime.datetime, not {}'.format(
                    type(start)))
        if not isinstance(end, datetime.datetime):
            raise TypeError(
                '"end" must be of type datetime.datetime, not {}'.format(
                    type(end)))
        if usage is not None and not isinstance(usage, dict):
            raise TypeError(
                '"usage" must be a dict, not {}'.format(type(usage)))
        self.start = start
        self.end = end
        self._usage = collections.OrderedDict()
        if usage:
            for key in sorted(usage.keys()):
                self.add_points(usage[key], key)

    def as_dict(self, legacy=False, mutable=False):
        output = {
            "period": {"begin": self.start, "end": self.end},
            "usage": {
                key: [v.as_dict(legacy=legacy, mutable=mutable) for v in val]
                for key, val in self._usage.items()
            },
        }
        return output if mutable else datastructures.ImmutableDict(output)

    def json(self, legacy=False):
        return json.dumps(self.as_dict(legacy=legacy, mutable=True))

    @classmethod
    def from_dict(cls, dict_, legacy=False):
        try:
            schema = DATAFRAME_SCHEMA
            if legacy:
                validator = functools.partial(DataPoint.from_dict, legacy=True)
                # NOTE(peschk_l): __name__ is required for voluptuous exception
                # message formatting
                validator.__name__ = 'DataPoint.from_dict'
                # NOTE(peschk_l): In case the legacy format is required, we
                # create a new schema where DataPoint.from_dict is called with
                # legacy=True. The "extend" method does create a new objects,
                # and replaces existing keys with new ones.
                schema = DATAFRAME_SCHEMA.extend({
                    voluptuous.Required('usage'): vutils.IterableValuesDict(
                        str, validator
                    ),
                })
            valid = schema(dict_)
            return cls(
                valid["period"]["begin"],
                valid["period"]["end"],
                usage=valid["usage"])
        except (voluptuous.error.Invalid, KeyError) as e:
            raise ValueError("{} isn't a valid DataFrame: {}".format(dict_, e))

    def add_points(self, points, type_):
        """Adds multiple points to the DataFrame

        :param points: DataPoints to add.
        :type point: list of DataPoints
        """
        if type_ in self._usage:
            self._usage[type_] += points
        else:
            self._usage[type_] = points

    def add_point(self, point, type_):
        """Adds a single point to the DataFrame

        :param point: DataPoint to add.
        :type point: DataPoint
        """
        if type_ in self._usage:
            self._usage[type_].append(point)
        else:
            self._usage[type_] = [point]

    def iterpoints(self):
        """Iterates over all datapoints of the dataframe.

        Yields (type, point) tuples.

        :rtype: (str, DataPoint)
        """
        for type_, points in self._usage.items():
            for point in points:
                yield type_, point

    def itertypes(self):
        """Iterates over all types of the dataframe.

        Yields (type, (point, )) tuples.

        :rtype: (str, (DataPoint, ))
        """
        for type_, points in self._usage.items():
            yield type_, points

    def __repr__(self):
        return 'DataFrame(metrics=[{}])'.format(','.join(self._usage.keys()))
