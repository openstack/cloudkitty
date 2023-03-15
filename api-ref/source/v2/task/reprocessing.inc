======================
Task schedule endpoint
======================
CloudKitty has a task endpoint `/v2/task/<type_of_task>`, which allows
operators to schedule administrative tasks, such as reprocessing.

Currently, the only task available is the reprocessing one, which is avaiable
via the following endpoints.

 - POST `/v2/task/reprocesses` -- to create a reprocessing task.
 - GET `/v2/task/reprocesses/<path_scope_id>` -- to retrieve a reprocessing task.
 - GET `/v2/task/reprocesses` -- to retrieve all reprocessing task.

Create a reprocessing task
==========================

The endpoint used to schedule a reprocessing task. The scheduled tasks are
loaded to execution once every processing cycle, as defined in the
CloudKitty `period` configuration.

.. rest_method::  POST `/v2/task/reprocesses`

.. rest_parameters:: task/reprocessing_parameters.yml

   - scope_ids: scope_ids
   - start_reprocess_time: start_reprocess_time
   - end_reprocess_time: end_reprocess_time
   - reason: reason

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

We will return an empty object as the response in case of success:

.. code-block:: javascript

   {}

Example
-------
.. code-block:: shell

   curl -s -X POST "https://<cloudkitty_server_and_port_here>/v2/task/reprocesses" -H "Accept: application/json" -H "User-Agent: python-keystoneclient" -H "X-Auth-Token: ${ACCESS_TOKEN_KEYSTONE}" -H "Content-Type: application/json" -d '{"reason": "Reprocessing test", "scope_ids": "<Some scope ID>", "start_reprocess_time": "2021-06-01 00:00:00+00:00", "end_reprocess_time": "2021-06-01 23:00:00+00:00"}'


The scope IDs can be retrieved via "/v2/scope" API, which is the API that one can use to list all scopes, and their status.

Retrieve a reprocessing task
============================

The endpoint used to retrieve a reprocessing task. By using this endpoint, one
can for instance check the progress of the reprocessing tasks.

.. rest_method::  GET `/v2/task/reprocesses/<path_scope_id>`

.. rest_parameters:: task/reprocessing_parameters.yml

   - path_scope_id: path_scope_id

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

We will return the scope data in case of a valid scope ID:

.. code-block:: javascript

   {"scope_id": "scope ID goes here",
    "reason": "The reason for this reprocessing for this scope",
    "start_reprocess_time": "2021-06-01 00:00:00+00:00",
    "end_reprocess_time": "2021-07-01 00:00:00+00:00",
    "current_reprocess_time": "2021-06-06 00:00:00+00:00"}

Example
-------
.. code-block:: shell

   curl -s -X GET "https://<cloudkitty_server_and_port_here>/v2/task/reprocesses/<scope ID goes here>" -H "Accept: application/json" -H "User-Agent: python-keystoneclient" -H "X-Auth-Token: ${ACCESS_TOKEN_KEYSTONE}"

Retrieve all reprocessing tasks
===============================

The endpoint used to retrieve all reprocessing tasks. By using this endpoint,
one can retrieve all reprocessing tasks scheduled for a scope.

.. rest_method::  GET `/v2/task/reprocesses`

.. rest_parameters:: task/reprocessing_parameters.yml

   - scope_ids: scope_ids_query
   - order: scope_ids_order_query

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

We will return the scope data in case of a valid scope ID:

.. code-block:: javascript

   [{"scope_id": "scope ID goes here",
    "reason": "The reason for this reprocessing for this scope",
    "start_reprocess_time": "2021-06-01 00:00:00+00:00",
    "end_reprocess_time": "2021-07-01 00:00:00+00:00",
    "current_reprocess_time": "2021-06-06 00:00:00+00:00"}]

Example
-------
.. code-block:: shell

   curl -s -X GET "https://<cloudkitty_server_and_port_here>/v2/task/reprocesses" -H "Accept: application/json" -H "User-Agent: python-keystoneclient" -H "X-Auth-Token: ${ACCESS_TOKEN_KEYSTONE}"