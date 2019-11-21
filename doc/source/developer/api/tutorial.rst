====================================
 Tutorial: creating an API endpoint
====================================

This section of the document details how to create an endpoint for CloudKitty's
v2 API. The v1 API is frozen, no endpoint should be added.

Setting up the layout for a new resource
========================================

In this section, we will create an ``example`` endpoint. Create the following
files and subdirectories in ``cloudkitty/api/v2/``:

.. code-block:: console

   cloudkitty/api/v2/
   └── example
       ├── example.py
       └── __init__.py


Creating a custom resource
==========================

Each v2 API endpoint is based on a Flask Blueprint and one Flask-RESTful
resource per sub-endpoint. This allows to have a logical grouping of the
resources. Let's take the ``/rating/hashmap`` route as an example. Each of
the hashmap module's resources should be a Flask-RESTful resource (eg.
``/rating/hashmap/service``, ``/rating/hashmap/field`` etc...).

.. note:: There should be a distinction between endpoints refering to a single
          resource and to several ones. For example, if you want an endpoint
          allowing to list resources of some kind, you should implement the
          following:

          * A ``MyResource`` resource with support for ``GET``, ``POST``
            and ``PUT`` HTTP methods on the ``/myresource/<uuid:>`` route.

          * A ``MyResourceList`` resource with support for the ``GET`` HTTP
            method on the ``/myresource`` route.

          * A blueprint containing these resources.


Basic resource
--------------

We'll create an ``/example/`` endpoint, used to manipulate fruits. We'll create
an ``Example`` resource, supporting ``GET`` and ``POST`` HTTP methods. First
of all, we'll create a class with ``get`` and ``post`` methods in
``cloudkitty/api/v2/example/example.py``:

.. code-block:: python

   from cloudkitty.api.v2 import base


   class Example(base.BaseResource):

       def get(self):
           pass

       def post(self):
           pass


Validating a method's parameters and output
-------------------------------------------

A ``GET`` request on our resource will simply return **{"message": "This is an
example endpoint"}**. The ``add_output_schema`` decorator adds voluptuous
validation to a method's output. This allows to set defaults.

.. autofunction:: cloudkitty.api.v2.utils.add_output_schema
   :noindex:

Let's update our ``get`` method in order to use this decorator:

.. code-block:: python

   import voluptuous

   from cloudkitty.api.v2 import base
   from cloudkitty import validation_utils


   class Example(base.BaseResource):

       @api_utils.add_output_schema({
           voluptuous.Required(
               'message',
               default='This is an example endpoint',
           ): validation_utils.get_string_type(),
       })
       def get(self):
           return {}


.. note:: In this snippet, ``get_string_type`` returns ``basestring`` in
          python2 and ``str`` in python3.

.. code-block:: console

   $ curl 'http://cloudkitty-api:8889/v2/example'
   {"message": "This is an example endpoint"}

It is now time to implement the ``post`` method. This function will take a
parameter. In order to validate it, we'll use the ``add_input_schema``
decorator:

.. autofunction:: cloudkitty.api.v2.utils.add_input_schema
   :noindex:

Arguments validated by the input schema are passed as named arguments to the
decorated function. Let's implement the post method. We'll use Werkzeug
exceptions for HTTP return codes.

.. code-block:: python

   @api_utils.add_input_schema('body', {
       voluptuous.Required('fruit'): validation_utils.get_string_type(),
   })
   def post(self, fruit=None):
       policy.authorize(flask.request.context, 'example:submit_fruit', {})
       if not fruit:
           raise http_exceptions.BadRequest(
               'You must submit a fruit',
           )
       if fruit not in ['banana', 'strawberry']:
           raise http_exceptions.Forbidden(
               'You submitted a forbidden fruit',
           )
       return {
           'message': 'Your fruit is a ' + fruit,
       }


Here, ``fruit`` is expected to be found in the request body:

.. code-block:: console

   $ curl -X POST -H 'Content-Type: application/json' 'http://cloudkitty-api:8889/v2/example' -d '{"fruit": "banana"}'
   {"message": "Your fruit is a banana"}


In order to retrieve ``fruit`` from the query, the function should have been
decorated like this:

.. code-block:: python

   @api_utils.add_input_schema('query', {
       voluptuous.Required('fruit'): api_utils.SingleQueryParam(str),
   })
   def post(self, fruit=None):

Note that a ``SingleQueryParam`` is used here: given that query parameters can
be specified several times (eg ``xxx?groupby=a&groupby=b``), Flask provides
query parameters as lists. The ``SingleQueryParam`` helper checks that a
parameter is provided only once, and returns it.

.. autoclass:: cloudkitty.api.v2.utils.SingleQueryParam
   :noindex:

.. warning:: ``SingleQueryParam`` uses ``voluptuous.Coerce`` internally for
             type checking. Thus, ``validation_utils.get_string_type`` cannot
             be used as ``basestring`` can't be instantiated.


Authorising methods
-------------------

The ``Example`` resource is still missing some authorisations. We'll create a
policy per method, configurable via the ``policy.yaml`` file. Create a
``cloudkitty/common/policies/v2/example.py`` file with the following content:

.. code-block:: python

   from oslo_policy import policy

   from cloudkitty.common.policies import base

   example_policies = [
       policy.DocumentedRuleDefault(
           name='example:get_example',
           check_str=base.UNPROTECTED,
           description='Get an example message',
           operations=[{'path': '/v2/example',
                        'method': 'GET'}]),
       policy.DocumentedRuleDefault(
           name='example:submit_fruit',
           check_str=base.UNPROTECTED,
           description='Submit a fruit',
           operations=[{'path': '/v2/example',
                        'method': 'POST'}]),
   ]


   def list_rules():
       return example_policies

Add the following lines to ``cloudkitty/common/policies/__init__.py``:

.. code-block:: python

   # [...]
   from cloudkitty.common.policies.v2 import example as v2_example


   def list_rules():
       return itertools.chain(
           base.list_rules(),
           # [...]
           v2_example.list_rules(),
       )

This registers two documented policies, ``get_example`` and ``submit_fruit``.
They are unprotected by default, which means that everybody can access them.
However, they can be overriden in ``policy.yaml``. Call them the following way:

.. code-block:: python

   # [...]
   import flask

   from cloudkitty.common import policy
   from cloudkitty.api.v2 import base

   class Example(base.BaseResource):
       # [...]
       def get(self):
           policy.authorize(flask.request.context, 'example:get_example', {})
           return {}

       # [...]
       def post(self):
           policy.authorize(flask.request.context, 'example:submit_fruit', {})
           # [...]


Loading drivers
---------------

Most of the time, resources need to load some drivers (storage, SQL...).
As the instantiation of these drivers can take some time, this should be done
only once.

Some drivers (like the storage driver) are loaded in ``BaseResource`` and are
thus available to all resources.

Resources requiring some additional drivers should implement the ``reload``
function:

.. code-block:: python

   class BaseResource(flask_restful.Resource):

       @classmethod
       def reload(cls):
           """Reloads all required drivers"""


Here's an example taken from ``cloudkitty.api.v2.scope.state.ScopeState``:

.. code-block:: python

   @classmethod
   def reload(cls):
       super(ScopeState, cls).reload()
       cls._client = messaging.get_client()
       cls._storage_state = storage_state.StateManager()


Registering resources
=====================

Each endpoint should provide an ``init`` method taking a Flask app as only
parameter. This method should call ``do_init``:

.. autofunction:: cloudkitty.api.v2.utils.do_init
   :noindex:

Add the following to ``cloudkitty/api/v2/example/__init__.py``:

.. code-block:: python

   from cloudkitty.api.v2 import utils as api_utils


   def init(app):
       api_utils.do_init(app, 'example', [
           {
               'module': __name__ + '.' + 'example',
               'resource_class': 'Example',
               'url': '',
           },
       ])
       return app

Here, we call ``do_init`` with the flask app passed as parameter, a blueprint
name, and a list of resources. The blueprint name will prefix the URLs of all
resources. Each resource is represented by a dict with the following
attributes:

* ``module``: name of the python module containing the resource class
* ``resource_class``: class of the resource
* ``url``: url suffix

In our case, the ``Example`` resource will be served at ``/example`` (blueprint
name + URL suffix).

.. note:: In case you need to add a resource to an existing endpoint, just add
          it to the list.

.. warning:: If you created a new module, you'll have to add it to
             ``API_MODULES`` in ``cloudkitty/api/v2/__init__.py``:

             .. code-block:: python

                API_MODULES = [
                    'cloudkitty.api.v2.example',
                ]


Documenting your endpoint
=========================

The v2 API is documented with `os_api_ref`_ . Each v2 API endpoint must be
documented in ``doc/source/api-reference/v2/<endpoint_name>/``.

.. _os_api_ref: https://docs.openstack.org/os-api-ref/latest/
