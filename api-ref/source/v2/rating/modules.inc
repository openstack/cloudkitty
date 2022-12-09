=======================
Rating modules endpoint
=======================

Get the list of modules
=======================

Returns the list of all rating modules loaded. This method does not require any
parameter.

.. rest_method::  GET /v2/rating/modules

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 400
   - 401
   - 403

Response
--------

.. rest_parameters:: rating/modules_parameters.yml

   - modules: modules_list

Response Example
----------------

.. literalinclude:: ./api_samples/rating/modules_list_get.json
   :language: javascript

Get one module
==============

Returns the details of one specific module. This method does not require any
parameter.

.. rest_method::  GET /v2/rating/modules/<module_id>

Status codes
------------

.. rest_status_code:: success http_status.yml

   - 200

.. rest_status_code:: error http_status.yml

   - 400
   - 401
   - 403
   - 404

Response
--------

.. rest_parameters:: rating/modules_parameters.yml

   - module_id: module_id
   - description: description
   - enabled: enabled
   - hot_config: hot_config
   - priority: priority

Response Example
----------------

.. literalinclude:: ./api_samples/rating/module_get.json
   :language: javascript
