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
import copy
import functools
import itertools

import requests

from cloudkitty.storage.v2.elasticsearch import client


class FakeElasticsearchClient(client.ElasticsearchClient):

    def __init__(self, *args, **kwargs):
        kwargs["autocommit"] = False
        super(FakeElasticsearchClient, self).__init__(*args, **kwargs)
        for method in ('get_index', 'put_mapping'):
            setattr(self, method, self.__base_response)

    @staticmethod
    def __base_response(*args, **kwargs):
        r = requests.Response()
        r.status_code = 200
        return r

    def commit(self):
        pass

    @staticmethod
    def __filter_func(begin, end, filters, mtypes, doc):
        type_filter = lambda doc: (  # noqa: E731
            doc['type'] in mtypes if mtypes else True)
        time_filter = lambda doc: (  # noqa: E731
            (doc['start'] >= begin if begin else True)
            and (doc['start'] < end if end else True))

        def filter_(doc):
            return all((doc['groupby'].get(k) == v
                        or (doc['metadata'].get(k) == v)
                        for k, v in filters.items())) if filters else True

        return type_filter(doc) and time_filter(doc) and filter_(doc)

    def retrieve(self, begin, end, filters, metric_types,
                 offset=0, limit=1000, paginate=True):
        filter_func = functools.partial(
            self.__filter_func, begin, end, filters, metric_types)
        output = list(filter(filter_func, self._docs))[offset:offset+limit]
        for doc in output:
            doc["start"] = doc["start"].isoformat()
            doc["end"] = doc["end"].isoformat()
            doc["_source"] = copy.deepcopy(doc)
        return len(output), output

    def total(self, begin, end, metric_types, filters, groupby,
              custom_fields=None, offset=0, limit=1000, paginate=True):
        filter_func = functools.partial(
            self.__filter_func, begin, end, filters, metric_types)
        docs = list(filter(filter_func, self._docs))
        if not groupby:
            return 1, [{
                'sum_qty': {'value': sum(doc['qty'] for doc in docs)},
                'sum_price': {'value': sum(doc['price'] for doc in docs)},
                'begin': begin,
                'end': end,
            }]

        output = []
        key_func = lambda d: tuple(  # noqa: E731
            d['type'] if g == 'type' else d['groupby'][g] for g in groupby)
        docs.sort(key=key_func)

        for groups, values in itertools.groupby(docs, key_func):
            val_list = list(values)
            output.append({
                'begin': begin,
                'end': end,
                'sum_qty': {'value': sum(doc['qty'] for doc in val_list)},
                'sum_price': {'value': sum(doc['price'] for doc in val_list)},
                'key': dict(zip(groupby, groups)),
            })
        return len(output), output[offset:offset+limit]

    def _req(self, method, url, data, params, deserialize=True):
        pass
