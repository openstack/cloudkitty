====================
Storage backend (v2)
====================

.. warning:: This backend is considered unstable and should be used for
             upstream development only.

In order to implement a storage backend for cloudkitty, you'll have to
implement the following abstract class:

.. autoclass:: cloudkitty.storage.v2.BaseStorage
   :members:

You'll then need to register an entrypoint corresponding to your storage
backend in the ``cloudkitty.storage.v2.backends`` section of the ``setup.cfg``
file.
