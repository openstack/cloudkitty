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

The response has the following format:

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

.. rest_parameters:: summary/summary_parameters.yml

   - begin: begin_resp
   - end: end_resp
   - qty: qty_resp
   - rate: rate_resp

Response Example
----------------

.. code-block:: shell

   curl "http://cloudkitty-api:8889/v2/summary?filters=project_id%3Afe9c35372db6420089883805b37a34af&groupby=type&groupby=project_id"

.. literalinclude:: ./api_samples/summary/summary_get.json
   :language: javascript
