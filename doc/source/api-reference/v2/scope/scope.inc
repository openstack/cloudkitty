====================
Scope state endpoint
====================

Get the status of several scopes
================================

Returns the status of several scopes.

.. rest_method::  GET /v2/scope

.. rest_parameters:: scope/scope_parameters.yml

   - collector: collector
   - fetcher: fetcher
   - limit: limit
   - offset: offset
   - scope_id: scope_id
   - scope_key: scope_key

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 400
   - 403
   - 404
   - 405

Response
--------

.. rest_parameters:: scope/scope_parameters.yml

   - collector: collector_resp
   - fetcher: fetcher_resp
   - state: state
   - scope_id: scope_id_resp
   - scope_key: scope_key_resp

Response Example
----------------

.. literalinclude:: ./api_samples/scope/scope_get.json
   :language: javascript


Reset the status of several scopes
==================================

Reset the status of several scopes.

.. rest_method::  PUT /v2/scope

.. rest_parameters:: scope/scope_parameters.yml

   - state: state
   - collector: collector_body
   - fetcher: fetcher_body
   - scope_id: scope_id_body
   - scope_key: scope_key_body
   - all_scopes: all_scopes

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 202

.. rest_status_code:: error http_status.yml

   - 400
   - 403
   - 404
   - 405
