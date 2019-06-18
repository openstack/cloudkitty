=========================
 Collector configuration
=========================

Common options
==============

Options common to all collectors are specified in the ``[collect]`` section of
the configuration file. The following options are available:

* ``collector``: Defaults to ``gnocchi``. The name of the collector to load.
  Must be one of [``gnocchi``, ``monasca``, ``prometheus``].

* ``period``: Default to 3600. Duration (in seconds) of the collect period.

* ``wait_periods``: Defaults to 2. Periods to wait before the current
  timestamp. This is done to avoid missing some data that hasn't been
  retrieved by the data source yet.

* ``metrics_conf``: Defaults to ``/etc/cloudkitty/metrics.yml``. Path of the
  metric collection configuration file. See "Metric collection" section below
  for details.

* ``scope_key``: Defaults to ``project_id``. Key at which the scope can be
  found. The scope defines how data collection is split between the processors.

Collector-specific options
==========================

Collector-specific options must be specified in the
``collector_{collector_name}`` section of ``cloudkitty.conf``.

Gnocchi
-------

Section: ``collector_gnocchi``.

* ``gnocchi_auth_type``: Defaults to ``keystone``. Defines what authentication
  method should be used by the gnocchi collector. Must be one of ``basic``
  (for gnocchi basic authentication) or ``keystone`` (for classic keystone
  authentication). If ``keystone`` is chosen, credentials can be specified
  in a section pointed at by the ``auth_section`` parameter.

* ``gnocchi_user``: For gnocchi basic authentication only. The gnocchi user.

* ``gnocchi_endpoint``: For gnocchi basic authentication only. The gnocchi
  endpoint.

* ``interface``: Defaults to ``internalURL``. For keystone authentication only.
  The interface to use for keystone URL discovery.

* ``region_name``: Defaults to ``RegionOne``. For keystone authentication only.
  Region name.


Monasca
-------

Section: ``collector_monasca``.

* ``interface``: Defaults to ``internal``. The interface to use for keystone
  URL discovery.

* ``monasca_service_name``: Defaults to ``monasca``. Name of the Monasca
  service in Keystone.

.. note:: By default, cloudkitty retrieves all metrics from Monasca in the
          project it is identified in. However, some metrics may need to be
          fetched from another tenant (for example if ceilometer is publishing
          metrics to monasca in the ``service`` tenant but monasca-agent is
          publishing metrics to the ``admin`` tenant). See the monasca-specific
          section in "Metric collection" below for details on how to configure
          this.

Prometheus
----------

Section ``collector_prometheus``.

* ``prometheus_url``: Prometheus HTTP API URL.

* ``prometheus_user``: For HTTP basic authentication. The username.

* ``prometheus_password``: For HTTP basic authentication. The password.

* ``cafile``: Option to allow custom certificate authority file.

* ``insecure``: Option to explicitly allow untrusted HTTPS connections.


Metric collection
=================

Metric collection is highly configurable in cloudkitty. In order to keep the
main configuration file as clean as possible, metric collection is configured
in a yaml file. The path to this file defaults to
``/etc/cloudkitty/metrics.yml``, but can be configured:

.. code-block:: ini

   [collect]
   metrics_conf = /my/custom/path.yml


Minimal Configuration
---------------------

This config file has the following format:

.. code-block:: yaml

   metrics: # top-level key
     metric_one: # metric name
       unit: squirrel
       groupby: # attributes by which metrics should be grouped
         - id
       metadata: # additional attributes to retrieve
         - color

At the top level of the file, a ``metrics`` key is required. It contains a dict
of metrics to collect, each key of the dict being the name of a metric as it is
called in the datasource (``volume.size`` or ``image.size`` for example).

For each metric, the following attributes are required:

* ``unit``: the unit in which the metric will be stored after conversion. This
  is just an indication for humans and has absolutely no impact on metric
  collection, conversion or rating.

* ``groupby``: A list of attributes by which metrics should be grouped
  on collection. These will allow to re-group data when it is retrieved
  through the v2 API. A typical usecase would be to group data by ID,
  project ID, domain ID and user ID on collection, but only by user ID
  on retrieval.

* ``metadata``: A list of additional attributes that should be collected for
  the given metric. These can be used for rating rules and will appear in
  monthly reports. However, it is not possible to group on these attributes.
  If you need to group on a ``metadata`` attribute, move it to the ``groupby``
  list.

.. note:: The ``scope_key`` is automatically added to ``groupby``.

Optional parameters
-------------------

Unit conversion
~~~~~~~~~~~~~~~

If you need to convert the collected qty (from MiB to GiB for example), it can
be done with the ``factor`` and ``offset`` options. ``factor`` defaults to 1
and ``offset`` to 0. These options are used to calculate the final result with
the following formula: ``qty = collected_qty * factor + offset``.

.. note:: ``factor`` and ``offset`` can be floats, integers or fractions.

Example from the default configuration file, conversion from B to MiB for the
``image.size`` metric:

.. code-block:: yaml

   metrics:
     image.size:
       groupby:
         - id
       metadata:
         - disk_format
       unit: MiB # Final unit
       factor: 1/1048576 # Dividing by 1024 * 1024

.. note::

   Here we don't add anything, so there is no need to specify ``offset``.

Quantity mutation
~~~~~~~~~~~~~~~~~

It is also possible to mutate the collected qty with the ``mutate`` option.
Four values are accepted for this parameter:

* ``NONE``: This is the default. The collected data is not modifed.

* ``CEIL``: The qty is rounded up to the closest integer.

* ``FLOOR``: The qty is rounded down to the closest integer.

* ``NUMBOOL``: If the collected qty equals 0, leave it at 0. Else, set it to 1.

.. warning::

   Quantity mutation is done **after** conversion. Example::

     factor: 10
     mutate: CEIL

   In consequence, the configuration above will convert 9.9 to 99
   (9.9 -> 99 -> 99) and not to 100 (9.9 -> 10 -> 100)

A typical usecase for the ``NUMBOOL`` conversion would be instance uptime
collection with the gnocchi collector: In order to know if an instance is
running or paused, you can use the ``cpu`` metric. This metric is at
0 when the instance is paused. Thus, the qty is mutated to a ``NUMBOOL``
because the ``cpu`` metric always represents one instance. Rating rules are
then defined based on the instance metadata. Example:

.. code-block:: yaml

   metrics:
     cpu:
       unit: instance
       mutate: NUMBOOL
       groupby:
         - id
       metadata:
         - flavor_id

Display name
~~~~~~~~~~~~

Sometimes, you'll want to use another name for a metric, either to shorten it a
bit or to make it more explicit. For example, the ``cpu`` metric from the
previous section could be called ``instance``. That's what the ``alt_name``
option does:

.. code-block:: yaml

   metrics:
     cpu:
       unit: instance
       alt_name: instance
       mutate: NUMBOOL
       groupby:
         - id
       metadata:
         - flavor_id

Collector-specific configuration
--------------------------------

Some collectors require extra options. These must be specified through the
``extra_args`` option. Some options have defaults, other must be systematically
specified. The extra args for each collector are detailed below.

Gnocchi
~~~~~~~

* ``resource_type``: No default value. The resource type the current metric is
  bound to.

* ``resource_key``: Defaults to ``id``. The attribute containing the unique
  resource identifier. This is an advanced option, do not modify it
  unless you know what you're doing.

* ``aggregation_method``: Defaults to ``max``. The aggregation method to use
  when retrieving measures from gnocchi. Must be one of ``min``, ``max``,
  ``mean``.

Monasca
~~~~~~~

* ``resource_key``: Defaults to ``resource_id``. The attribute containing the
  unique resource identifier. This is an advanced option, do not modify it
  unless you know what you're doing.

* ``aggregation_method``: Defaults to ``max``. The aggregation method to use
  when retrieving measures from monasca. Must be one of ``min``, ``max``,
  ``mean``.

* ``forced_project_id``: Defaults to None. Force the given metric to be
  fetched from a specific tenant instead of the one cloudkitty is identified
  in. For example, if cloudkitty is identified in the ``service`` project, but
  needs to fetch a metric from the ``admin`` project, its ID should be
  specified through this option.

Prometheus
~~~~~~~~~~

* ``aggregation_method``: Defaults to ``max``. The aggregation method to use
  when retrieving measures from prometheus. Must be one of ``avg``, ``min``,
  ``max``, ``sum``, ``count``, ``stddev``, ``stdvar``.
