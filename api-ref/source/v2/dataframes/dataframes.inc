===================
Dataframes endpoint
===================

Add dataframes into the storage backend
=======================================

Add dataframes into the storage backend.

.. rest_method::  POST /v2/dataframes

.. rest_parameters:: dataframes/dataframes_parameters.yml

   - dataframes: dataframes_body

Request Example
---------------

In the body:

.. literalinclude:: ./api_samples/dataframes/dataframes_post.json
   :language: javascript

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 204

.. rest_status_code:: error http_status.yml

   - 400
   - 401
   - 403
   - 405

Response
--------

No content is to be returned.

Get dataframes from the storage backend
============================================

Get dataframes from the storage backend.

.. rest_method::  GET /v2/dataframes

.. rest_parameters:: dataframes/dataframes_parameters.yml

   - limit: limit
   - offset: offset
   - begin: begin
   - end: end
   - filters: filters

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 400
   - 401
   - 403
   - 405

Response
--------

.. rest_parameters:: dataframes/dataframes_parameters.yml

   - total: total_resp
   - dataframes: dataframes_resp

Response Example
----------------

.. literalinclude:: ./api_samples/dataframes/dataframes_get.json
   :language: javascript

