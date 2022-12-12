================
Summary endpoint
================

Get a rating summary
====================

Get a rating summary for one or several tenants.

.. rest_method::  GET /v2/summary

.. rest_parameters:: summary/summary_parameters.yml

   - limit: limit
   - offset: offset
   - begin: begin
   - end: end
   - groupby: groupby
   - filters: filters
   - custom_fields: custom_fields
   - response_format: response_format

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 400
   - 403
   - 405

Response
--------

The response has the following default format (response_format='table'):

.. code-block:: javascript

   {
       "columns": [
           "begin",
           "end",
           "qty",
           "rate",
           "group1",
           "group2",
       ],
       "results": [
           [
               "2019-06-01T00:00:00Z",
               "2019-07-01T00:00:00Z",
               2590.421676635742,
               1295.210838317871,
               "group1",
               "group2",
           ]
       ],
       "total": 4
   }

``total`` is the total amount of found elements. ``columns`` contains the name of
the columns for each element of ``results``. The columns are the four mandatory ones
(``begin``, ``end``, ``qty``, ``rate``) along with each attribute the result is
grouped by.

``format`` is the response format. It can be "table" or "object". The default
response structure is "table", which is presented above. The object structure
uses the following pattern.

.. code-block:: javascript

   {
       "results": [
           {"begin": "2019-06-01T00:00:00Z",
            "end": "2019-07-01T00:00:00Z",
            "qty": 2590.421676635742,
            "rate": 1295.210838317871,
            "group1": "group1",
            "group2": "group2",
           },
       ],
       "total": 4
   }

.. note:: It is also possible to group data by time, in order to obtain timeseries.
          In order to do this, group by ``time``. No extra column will be added,
          but you'll get one entry per collect period in the queried timeframe.
          See examples below.

.. rest_parameters:: summary/summary_parameters.yml

   - begin: begin_resp
   - end: end_resp
   - qty: qty_resp
   - rate: rate_resp

Response Example
----------------

Grouping by time and project_id:

.. code-block:: shell

   curl "http://cloudkitty-api:8889/v2/summary?groupby=time&groupby=project_id&limit=3"

.. literalinclude:: ./api_samples/summary/summary_get_groupby_time.json
   :language: javascript

.. code-block:: shell

   curl "http://cloudkitty-api:8889/v2/summary?filters=project_id%3Afe9c35372db6420089883805b37a34af&groupby=type&groupby=project_id"

.. literalinclude:: ./api_samples/summary/summary_get.json
   :language: javascript
