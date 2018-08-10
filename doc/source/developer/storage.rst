====================
Storage backend (v2)
====================

.. warning:: This backend is considered unstable and should be used for upstream
             development only.

In order to implement a storage backend for cloudkitty, you'll have to implement
the following abstract class:

.. autoclass:: cloudkitty.storage.v2.BaseStorage
   :members:

You'll then need to register an entrypoint corresponding to your storage backend
in the ``cloudkitty.storage.v2.backends`` section of the ``setup.cfg`` file.

Testing
=======

There is a generic test class for v2 storage backends. It allows to run a
functional test suite against a new v2 storage backend.

.. code:: shell

   $ tree cloudkitty/tests/storage/v2
   cloudkitty/tests/storage/v2
   ├── base_functional.py
   ├── __init__.py
   └── test_gnocchi_functional.py

In order to use the class, add a file called ``test_mybackend_functional.py``
to the ``cloudkitty/tests/storage/v2`` directory. You will then need to write a
class inheriting from ``BaseFunctionalStorageTest``. Specify the storage version
and the backend name as class attributes

Example:

.. code:: python

   import testtools

   from cloudkitty.tests.storage.v2 import base_functional
   from cloudkitty.tests.utils import is_functional_test


   @testtools.skipUnless(is_functional_test(), 'Test is not a functional test')
   class GnocchiBaseFunctionalStorageTest(
           base_functional.BaseFunctionalStorageTest):

       storage_backend = 'gnocchi'
       storage_version = 2


Two methods need to be implemented:

* ``wait_for_backend``. This method is called once data has been once
  dataframes have been pushed to the storage backend (in gnocchi's case, it
  waits for all measures to have been processed). It is a classmethod.

* ``cleanup_backend``: This method is called at the end of the test suite in
  order to delete all data from the storage backend. It is a classmethod.
