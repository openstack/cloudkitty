================
Example endpoint
================

Get an example message
======================

Returns an example message.

.. rest_method::  GET /v2/example

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 405

Response
--------

.. rest_parameters:: example/example_parameters.yml

   - msg: example_msg


Submit a fruit
==============

Returns the fruit you sent.

.. rest_method::  POST /v2/example

.. rest_parameters:: example/example_parameters.yml

   - fruit: fruit

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200
   - 400

.. rest_status_code:: error http_status.yml

   - 400
   - 403: fruit_error
   - 405

Response
--------

.. rest_parameters:: example/example_parameters.yml

   - msg: fruit_msg
