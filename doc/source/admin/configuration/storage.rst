===============================
 Storage backend configuration
===============================

Common options
==============

.. note::

   Two storage backend interfaces are available: v1 and v2. Each supports one
   or several drivers. The v2 storage interface is required to use
   CloudKitty's v2 API. It is retrocompatible with the v1 API. However, it is
   not possible to use the v2 API with the v1 storage interface.

The main storage backend options are specified in the ``[storage]`` section of
the configuration file. The following options are available:

* ``version``: Defaults to 2. Version of the storage interface to use
  (must be 1 or 2).

* ``backend``: Defaults to ``influxdb``. Storage driver to use.
  Supported v1 drivers are:

  - ``sqlalchemy``

  Supported v2 drivers are:

  - ``influxdb``
  - ``elasticsearch``
  - ``opensearch``

Driver-specific options
=======================

SQLAlchemy (v1)
---------------

This backend has no specific options. It uses the ``connection`` option of the
``database`` section. Example of value for this option:

.. code-block:: ini

   [database]

   connection = mysql+pymysql://cloudkitty_user:cloudkitty_password@mariadb_host/cloudkitty_database

InfluxDB (v2)
-------------

Section: ``storage_influxdb``.

* ``username``: InfluxDB username.

* ``password``: InfluxDB password.

* ``database``: InfluxDB database.

* ``retention_policy``: Retention policy to use (defaults to ``autogen``)

* ``host``: Defaults to ``localhost``. InfluxDB host.

* ``port``: Default to 8086. InfluxDB port.

* ``use_ssl``: Defaults to false. Set to true to use SSL for InfluxDB
  connections.

* ``insecure``: Defaults to false. Set to true to authorize insecure HTTPS
  connections to InfluxDB.

* ``cafile``: Path of the CA certificate to trust for HTTPS connections.


.. note:: CloudKitty will push one point per collected metric per collect
          period to InfluxDB. Depending on the size of your infra and the
          capacities of your InfluxDB host / cluster, you might want to do
          regular exports of your data and create a custom retention policy on
          cloudkitty's database.

Elasticsearch (v2)
------------------

Section ``storage_elasticsearch``:

* ``host``: Defaults to ``http://localhost:9200``. Elasticsearch host, along
  with port and protocol.

* ``index_name``: Defaults to ``cloudkitty``. Elasticsearch index to use.

* ``insecure``: Defaults to ``false``. Set to true to allow insecure HTTPS
  connections to Elasticsearch.

* ``cafile``: Path of the CA certificate to trust for HTTPS connections.

* ``scroll_duration``: Defaults to 30. Duration (in seconds) for which the
  Elasticsearch scroll contexts should be kept alive.

OpenSearch 2.x (v2)
-------------------

Section ``storage_opensearch``:

* ``host``: Defaults to ``http://localhost:9200``. OpenSearch 2.x host, along
  with port and protocol.

* ``index_name``: Defaults to ``cloudkitty``. OpenSearch index to use.

* ``insecure``: Defaults to ``false``. Set to true to allow insecure HTTPS
  connections to OpenSearch.

* ``cafile``: Path of the CA certificate to trust for HTTPS connections.

* ``scroll_duration``: Defaults to 30. Duration (in seconds) for which the
  OpenSearch scroll contexts should be kept alive.
