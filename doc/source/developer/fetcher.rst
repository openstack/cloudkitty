===============
 Scope fetcher
===============

The fetcher retrieves a list of scopes to rate. These scopes are then passed to
the collector, in combination with each metric type.

Implementation
==============

Fetchers are extremely simple. A custom fetcher must implement the following
class:

.. autoclass:: cloudkitty.fetcher.BaseFetcher
   :members: get_tenants

The ``get_tenants`` method takes no parameters and returns a list of unique
scope_ids, represented as ``str``.

The name of the new fetcher must be specified as a class attribute.

Options for the new fetcher must be registered under the ``fetcher_<name>``
config section.

A new scope fetcher must be implemented in a new module, in
``cloudkitty.fetcher.<name>.py``. Its class must be called ``<Name>Fetcher``.

An entrypoint must be registered for new fetchers. This is done in the
``setup.cfg`` file, located at the root of the repository:

.. code-block:: ini

   cloudkitty.fetchers =
       keystone = cloudkitty.fetcher.keystone:KeystoneFetcher
       source = cloudkitty.fetcher.source:SourceFetcher
       # [...]
       custom = cloudkitty.fetcher.custom:CustomFetcher

Example
=======

The most simple scope fetcher is the ``SourceFetcher``. It simply returns a
list of scopes read from the configuration file:

.. code-block:: python

   # In cloudkitty/fetcher/source.py
   from oslo_config import cfg

   from cloudkitty import fetcher

   FETCHER_SOURCE_OPTS = 'fetcher_source'

   fetcher_source_opts = [
       cfg.ListOpt(
           'sources',
           default=list(),
           help='list of source identifiers',
       ),
   ]

   # Registering the 'sources' option in the 'fetcher_source' option
   cfg.CONF.register_opts(fetcher_source_opts, FETCHER_SOURCE_OPTS)

   CONF = cfg.CONF


   class SourceFetcher(fetcher.BaseFetcher):

       # Defining the name of the fetcher
       name = 'source'

       # Returning the list of scopes read from the configuration file
       def get_tenants(self):
           return CONF.fetcher_source.sources


More complex examples can be found in the ``cloudkitty/fetcher`` directory.
