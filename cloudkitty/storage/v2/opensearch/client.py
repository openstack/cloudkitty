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
import itertools

from oslo_log import log
import requests

from cloudkitty.storage.v2.opensearch import exceptions
from cloudkitty.utils import json

LOG = log.getLogger(__name__)


class OpenSearchClient(object):
    """Class used to ease interaction with OpenSearch.

    :param autocommit: Defaults to True. Automatically push documents to
                       OpenSearch once chunk_size has been reached.
    :type autocommit: bool
    :param chunk_size: Maximal number of documents to commit/retrieve at once.
    :type chunk_size: int
    :param scroll_duration: Defaults to 60. Duration, in seconds, for which
                            search contexts should be kept alive
    :type scroll_duration: int
    """

    def __init__(self, url, index_name, mapping_name,
                 verify=True,
                 autocommit=True,
                 chunk_size=5000,
                 scroll_duration=60):
        self._url = url.strip('/')
        self._index_name = index_name.strip('/')
        self._mapping_name = mapping_name.strip('/')
        self._autocommit = autocommit
        self._chunk_size = chunk_size
        self._scroll_duration = str(scroll_duration) + 's'
        self._scroll_params = {'scroll': self._scroll_duration}

        self._docs = []
        self._scroll_ids = set()

        self._sess = requests.Session()
        self._verify = self._sess.verify = verify
        self._sess.headers = {'Content-Type': 'application/json'}

    @staticmethod
    def _log_query(url, query, response):
        message = 'Query on {} with body "{}" took {}ms'.format(
            url, query, response['took'])
        if 'hits' in response.keys():
            message += ' for {} hits'.format(response['hits']['total'])
        LOG.debug(message)

    @staticmethod
    def _build_must(start, end, metric_types, filters):
        must = []
        if start:
            must.append({"range": {"start": {"gte": start.isoformat()}}})
        if end:
            must.append({"range": {"end": {"lte": end.isoformat()}}})

        if filters and 'type' in filters.keys():
            must.append({'term': {'type': filters['type']}})

        if metric_types:
            must.append({"terms": {"type": metric_types}})

        return must

    @staticmethod
    def _build_should(filters):
        if not filters:
            return []

        should = []
        for k, v in filters.items():
            if k != 'type':
                should += [{'term': {'groupby.' + k: v}},
                           {'term': {'metadata.' + k: v}}]
        return should

    def _build_composite(self, groupby):
        if not groupby:
            return []
        sources = []
        for elem in groupby:
            if elem == 'type':
                sources.append({'type': {'terms': {'field': 'type.keyword'}}})
            elif elem == 'time':
                # Not doing a date_histogram aggregation because we don't know
                # the period
                sources.append({'begin': {'terms': {'field': 'start'}}})
                sources.append({'end': {'terms': {'field': 'end'}}})
            else:
                field = 'groupby.' + elem + '.keyword'
                sources.append({elem: {'terms': {'field': field}}})

        return {"sources": sources}

    @staticmethod
    def _build_query(must, should, composite):
        query = {}

        if must or should:
            query["query"] = {"bool": {}}

        if must:
            query["query"]["bool"]["must"] = must

        if should:
            query["query"]["bool"]["should"] = should
            # We want each term to match exactly once, and each term introduces
            # two "term" aggregations: one for "groupby" and one for "metadata"
            query["query"]["bool"]["minimum_should_match"] = len(should) // 2

        if composite:
            query["aggs"] = {"sum_and_price": {
                "composite": composite,
                "aggregations": {
                    "sum_price": {"sum": {"field": "price"}},
                    "sum_qty": {"sum": {"field": "qty"}},
                }
            }}

        return query

    def _req(self, method, url, data, params, deserialize=True):
        r = method(url, data=data, params=params)
        if r.status_code < 200 or r.status_code >= 300:
            raise exceptions.InvalidStatusCode(
                200, r.status_code, r.text, data)
        if not deserialize:
            return r
        output = r.json()
        self._log_query(url, data, output)
        return output

    def post_mapping(self, mapping):
        """Does a POST request against OpenSearch's mapping API.

        The POST request will be done against
        `/<index_name>/<mapping_name>`

        :mapping: body of the request
        :type mapping: dict
        :rtype: requests.models.Response
        """
        url = '/'.join(
            (self._url, self._index_name, self._mapping_name))
        return self._req(
            self._sess.post, url, json.dumps(mapping), {}, deserialize=False)

    def get_index(self):
        """Does a GET request against OpenSearch's index API.

        The GET request will be done against `/<index_name>`

        :rtype: requests.models.Response
        """
        url = '/'.join((self._url, self._index_name))
        return self._req(self._sess.get, url, None, None, deserialize=False)

    def search(self, body, scroll=True):
        """Does a GET request against OpenSearch's search API.

        The GET request will be done against `/<index_name>/_search`

        :param body: body of the request
        :type body: dict
        :rtype: dict
        """
        url = '/'.join((self._url, self._index_name, '_search'))
        params = self._scroll_params if scroll else None
        return self._req(
            self._sess.get, url, json.dumps(body), params)

    def scroll(self, body):
        """Does a GET request against OpenSearch's scroll API.

        The GET request will be done against `/_search/scroll`

        :param body: body of the request
        :type body: dict
        :rtype: dict
        """
        url = '/'.join((self._url, '_search/scroll'))
        return self._req(self._sess.get, url, json.dumps(body), None)

    def close_scroll(self, body):
        """Does a DELETE request against OpenSearch's scroll API.

        The DELETE request will be done against `/_search/scroll`

        :param body: body of the request
        :type body: dict
        :rtype: dict
        """
        url = '/'.join((self._url, '_search/scroll'))
        resp = self._req(
            self._sess.delete, url, json.dumps(body), None, deserialize=False)
        body = resp.json()
        LOG.debug('Freed {} scrolls contexts'.format(body['num_freed']))
        return body

    def close_scrolls(self):
        """Closes all scroll contexts opened by this client."""
        ids = list(self._scroll_ids)
        LOG.debug('Closing {} scroll contexts: {}'.format(len(ids), ids))
        self.close_scroll({'scroll_id': ids})
        self._scroll_ids = set()

    def bulk_with_instruction(self, instruction, terms):
        """Does a POST request against OpenSearch's bulk API

        The POST request will be done against
        `/<index_name>/_bulk`

        The instruction will be appended before each term. For example,
        bulk_with_instruction('instr', ['one', 'two']) will produce::

           instr
           one
           instr
           two

        :param instruction: instruction to execute for each term
        :type instruction: dict
        :param terms: list of terms for which instruction should be executed
        :type terms: collections.abc.Iterable
        :rtype: requests.models.Response
        """
        instruction = json.dumps(instruction)
        data = '\n'.join(itertools.chain(
            *[(instruction, json.dumps(term)) for term in terms]
        )) + '\n'
        url = '/'.join(
            (self._url, self._index_name, '_bulk'))
        return self._req(self._sess.post, url, data, None, deserialize=False)

    def bulk_index(self, terms):
        """Indexes each of the documents in 'terms'

        :param terms: list of documents to index
        :type terms: collections.abc.Iterable
        """
        LOG.debug("Indexing {} documents".format(len(terms)))
        return self.bulk_with_instruction({"index": {}}, terms)

    def commit(self):
        """Index all documents"""
        while self._docs:
            self.bulk_index(self._docs[:self._chunk_size])
            self._docs = self._docs[self._chunk_size:]

    def add_point(self, point, type_, start, end):
        """Append a point to the client.

        :param point: DataPoint to append
        :type point: cloudkitty.dataframe.DataPoint
        :param type_: type of the DataPoint
        :type type_: str
        """
        self._docs.append({
            'start': start,
            'end': end,
            'type': type_,
            'unit': point.unit,
            'qty': point.qty,
            'price': point.price,
            'groupby': point.groupby,
            'metadata': point.metadata,
        })
        if self._autocommit and len(self._docs) >= self._chunk_size:
            self.commit()

    def _get_chunk_size(self, offset, limit, paginate):
        if paginate and offset + limit < self._chunk_size:
            return offset + limit
        return self._chunk_size

    def retrieve(self, begin, end, filters, metric_types,
                 offset=0, limit=1000, paginate=True):
        """Retrieves a paginated list of documents from OpenSearch."""
        if not paginate:
            offset = 0

        query = self._build_query(
            self._build_must(begin, end, metric_types, filters),
            self._build_should(filters), None)
        query['size'] = self._get_chunk_size(offset, limit, paginate)

        resp = self.search(query)

        scroll_id = resp['_scroll_id']
        self._scroll_ids.add(scroll_id)
        total_hits = resp['hits']['total']

        if isinstance(total_hits, dict):
            LOG.debug("Total hits [%s] is a dict. Therefore, we only extract "
                      "the 'value' attribute as the total option.", total_hits)
            total_hits = total_hits.get("value")

        total = total_hits
        chunk = resp['hits']['hits']

        output = chunk[offset:offset+limit if paginate else len(chunk)]
        offset = 0 if len(chunk) > offset else offset - len(chunk)

        while (not paginate) or len(output) < limit:
            resp = self.scroll({
                'scroll_id': scroll_id,
                'scroll': self._scroll_duration,
            })

            scroll_id, chunk = resp['_scroll_id'], resp['hits']['hits']
            self._scroll_ids.add(scroll_id)
            # Means we've scrolled until the end
            if not chunk:
                break

            output += chunk[offset:offset+limit if paginate else len(chunk)]
            offset = 0 if len(chunk) > offset else offset - len(chunk)

        self.close_scrolls()
        return total, output

    def delete_by_query(self, begin=None, end=None, filters=None):
        """Does a POST request against ES's Delete By Query API.

        The POST request will be done against
        `/<index_name>/_delete_by_query`

        :param filters: Optional filters for documents to delete
        :type filters: list of dicts
        :rtype: requests.models.Response
        """
        url = '/'.join((self._url, self._index_name, '_delete_by_query'))
        must = self._build_must(begin, end, None, filters)
        data = (json.dumps({"query": {"bool": {"must": must}}})
                if must else None)
        return self._req(self._sess.post, url, data, None)

    def total(self, begin, end, metric_types, filters, groupby,
              custom_fields=None, offset=0, limit=1000, paginate=True):

        if custom_fields:
            LOG.warning("'custom_fields' are not implemented yet for "
                        "OpenSearch. Therefore, the custom fields [%s] "
                        "informed by the user will be ignored.", custom_fields)
        if not paginate:
            offset = 0

        must = self._build_must(begin, end, metric_types, filters)
        should = self._build_should(filters)
        composite = self._build_composite(groupby) if groupby else None
        if composite:
            composite['size'] = self._chunk_size
        query = self._build_query(must, should, composite)

        if "aggs" not in query.keys():
            query["aggs"] = {
                "sum_price": {"sum": {"field": "price"}},
                "sum_qty": {"sum": {"field": "qty"}},
            }

        query['size'] = 0

        resp = self.search(query, scroll=False)

        # Means we didn't group, so length is 1
        if not composite:
            return 1, [resp["aggregations"]]

        after = resp["aggregations"]["sum_and_price"].get("after_key")
        chunk = resp["aggregations"]["sum_and_price"]["buckets"]

        total = len(chunk)

        output = chunk[offset:offset+limit if paginate else len(chunk)]
        offset = 0 if len(chunk) > offset else offset - len(chunk)

        # FIXME(peschk_l): We have to iterate over ALL buckets in order to get
        # the total length. If there is a way for composite aggregations to get
        # the total amount of buckets, please fix this
        while after:
            composite_query = query["aggs"]["sum_and_price"]["composite"]
            composite_query["size"] = self._chunk_size
            composite_query["after"] = after
            resp = self.search(query, scroll=False)
            after = resp["aggregations"]["sum_and_price"].get("after_key")
            chunk = resp["aggregations"]["sum_and_price"]["buckets"]
            if not chunk:
                break
            output += chunk[offset:offset+limit if paginate else len(chunk)]
            offset = 0 if len(chunk) > offset else offset - len(chunk)
            total += len(chunk)

        if paginate:
            output = output[offset:offset+limit]
        return total, output
