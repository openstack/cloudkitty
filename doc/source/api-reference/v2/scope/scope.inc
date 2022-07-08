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
   - last_processed_timestamp: last_processed_timestamp
   - scope_id: scope_id_resp
   - scope_key: scope_key_resp
   - active: active_key_resp

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
   - last_processed_timestamp: last_processed_timestamp
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

Patch a scope
================================

Patches/updates a scope.

.. rest_method::  PATCH /v2/scope

.. rest_parameters:: scope/scope_parameters.yml

   - collector: collector
   - fetcher: fetcher
   - limit: limit
   - offset: offset
   - scope_id: scope_id
   - scope_key: scope_key
   - active: active_body

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
   - active: active_key_resp


Response Example
----------------

.. literalinclude:: ./api_samples/scope/scope_get.json
   :language: javascript

Create a scope
================================

Create a scope.

.. rest_method::  POST /v2/scope

.. rest_parameters:: scope/scope_parameters.yml

   - collector: collector
   - fetcher: fetcher
   - scope_id: scope_id
   - scope_key: scope_key
   - active: active_body

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

   - scope_id: scope_id_resp
   - scope_key: scope_key_resp
   - fetcher: fetcher_resp
   - collector: collector_resp
   - state: state
   - last_processed_timestamp: last_processed_timestamp
   - active: active_key_resp
   - scope_activation_toggle_date: scope_activation_toggle_date


Response Example
----------------

.. literalinclude:: ./api_samples/scope/scope_get.json
   :language: javascript
