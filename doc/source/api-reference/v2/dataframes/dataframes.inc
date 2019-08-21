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
