
=========================
 Collector configuration
=========================

Common options
==============

Options common to all collectors are specified in the ``[collect]`` section of
the configuration file. The following options are available:

* ``collector``: Defaults to ``gnocchi``. The name of the collector to load.
  Must be one of [``gnocchi``, ``prometheus``].

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
Five values are accepted for this parameter:

* ``NONE``: This is the default. The collected data is not modifed.

* ``CEIL``: The qty is rounded up to the closest integer.

* ``FLOOR``: The qty is rounded down to the closest integer.

* ``NUMBOOL``: If the collected qty equals 0, leave it at 0. Else, set it to 1.

* ``NOTNUMBOOL``: If the collected qty equals 0, set it to 1. Else, set it to
  0.

* ``MAP``: Map arbritrary values to new values as defined through the
  ``mutate_map`` option (dictionary). If the value is not found in
  ``mutate_map``, set it to 0. If ``mutate_map`` is not defined or is empty,
  all values are set to 0.

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

The ``NOTNUMBOOL`` mutator is useful for status-like metrics where 0 denotes
the billable state. For example the following Prometheus metric has value of 0
when the instance is in ACTIVE state but 4 if the instance is in ERROR state:

.. code-block:: yaml

   metrics:
     openstack_nova_server_status:
       unit: instance
       mutate: NOTNUMBOOL
       groupby:
         - id
       metadata:
         - flavor_id

The ``MAP`` mutator is useful when multiple statuses should be billabled. For
example, the following Prometheus metric has a value of 0 when the instance is
in ACTIVE state, but operators may want to rate other non-zero states:

.. code-block:: yaml

   metrics:
     openstack_nova_server_status:
       unit: instance
       mutate: MAP
       mutate_map:
         0.0: 1.0  # ACTIVE
         11.0: 1.0 # SHUTOFF
         12.0: 1.0 # SUSPENDED
         16.0: 1.0 # PAUSED
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

Metric description
~~~~~~~~~~~~~~~~~~

Sometimes, you will want to use a more descriptive attribute to show more
details about the configured rating type. For instance, to provide more
details about the rating of operating system licenses or other software
licenses configured in the cloud. For that, we have the option called
``description``, which is a String like field (up to 64 kB) that can be
used to provide more information for a rating of a metric. When configured,
this option is persisted as rating metadata and it is available through the
summary GET API.

.. code-block:: yaml

   metrics:
     instance-status:
       unit: license-hours
       alt_name: license-hours
       description: |
                    Operating system licenses are charged as follows: (i)
                    Linux distro will not be charged; (ii) All Windows up to
                    version 8 are charged .01 every hour, and other versions
                    .5; (iii) Any other operating systems will be charged .02
       groupby:
         - id
         - operating_system_name
         - operating_system_distro
         - operating_system_version
         - flavor_id
         - flavor_name
         - cores
         - ram
       metadata: []

Collector-specific configuration
--------------------------------

Some collectors require extra options. These must be specified through the
``extra_args`` option. Some options have defaults, other must be systematically
specified. The extra args for each collector are detailed below.

Gnocchi
~~~~~~~

Besides the common configuration, the Gnocchi collector also accepts a list of
rating types definitions for each metric. Using a list of rating types
definitions allows operators to rate different aspects of the same resource
type collected through the same metric in Gnocchi, otherwise operators would
need to create multiple metrics in Gnocchi to create multiple rating types in
CloudKitty.

.. code-block:: yaml

   metrics:
     instance.metric:
       - unit: instance
         alt_name: flavor
         mutate: NUMBOOL
         groupby:
           - id
         metadata:
           - flavor_id
       - unit: instance
         alt_name: operating_system_license
         mutate: NUMBOOL
         groupby:
           - id
         metadata:
           - os_license


.. note:: In order to retrieve metrics from Gnocchi, Cloudkitty uses the
          dynamic aggregates endpoint. It builds an operation of the following
          format: ``(aggregate RE_AGGREGATION_METHOD (metric METRIC_NAME
          AGGREGATION_METHOD))``. This means "retrieve all aggregates of type
          ``AGGREGATION_METHOD`` for the metric named ``METRIC_NAME`` and
          re-aggregate them using ``RE_AGGREGATION_METHOD``".

          By default, the re-aggregation method defaults to the
          aggregation method.

          Setting the re-aggregation method to a different value than the
          aggregation method is useful when the granularity of the aggregates
          does not match CloudKitty's collect period, or when using
          ``rate:`` aggregation, as you're probably don't want a rate of rates,
          but rather a sum or max of rates.


* ``resource_type``: No default value. The resource type the current metric is
  bound to.

* ``resource_key``: Defaults to ``id``. The attribute containing the unique
  resource identifier. This is an advanced option, do not modify it
  unless you know what you're doing.

* ``aggregation_method``: Defaults to ``max``. The aggregation method to use
  when retrieving measures from gnocchi. Must be one of ``min``, ``max``,
  ``mean``, ``rate:min``, ``rate:max``, ``rate:mean``.

* ``re_aggregation_method``: Defaults to ``aggregation_method``. The
  re_aggregation method to use when retrieving measures from gnocchi.

* ``force_granularity``: Defaults to ``0``. If > 0, this granularity will be
  used for metric aggregations. Else, the lowest available granularity will be
  used (meaning the granularity covering the longest period).

* ``use_all_resource_revisions``: Defaults to ``True``. This option is useful
  when using Gnocchi with the patch introduced via https://github
  .com/gnocchixyz/gnocchi/pull/1059. That patch can cause queries to return
  more than one entry per granularity (timespan), according to the revisions a
  resource has. This can be problematic when using the 'mutate' option
  of Cloudkitty. This option to allow operators to discard all datapoints
  returned from Gnocchi, but the last one in the granularity queried by
  CloudKitty for a resource id. The default behavior is maintained, which
  means, CloudKitty always use all of the data points returned.

* ``custom_query``: Provide means for operators to customize the aggregation
  query executed against Gnocchi. By default we use the following ``(aggregate
  RE_AGGREGATION_METHOD (metric METRIC_NAME AGGREGATION_METHOD))``. Therefore,
  this option enables operators to take full advantage of operations available
  in Gnocchi such as any arithmetic operations, logical operations and many
  others. When using a custom aggregation query, you can keep the placeholders
  ``RE_AGGREGATION_METHOD``, ``AGGREGATION_METHOD``, and ``METRIC_NAME``: they
  will be replaced at runtime by values from the metric configuration.

  One example use case is metrics that are supposed to be always growing
  values, such as RadosGW usage data. The usage data is affected by usage data
  trimming on RadosGW, which can lead to swaps (meaning, that the right side
  value of the series is smaller than the left side value) in the data series
  in Gnocchi. Therefore, to handle this situation one could, for instance, use
  the following custom query: ``(div (+ (aggregate RE_AGGREGATION_METHOD
  (metric METRIC_NAME AGGREGATION_METHOD)) (abs (aggregate
  RE_AGGREGATION_METHOD (metric METRIC_NAME AGGREGATION_METHOD)))) 2)``: this
  custom query would return ``0`` when the value of the series swap.


Prometheus
~~~~~~~~~~

* ``aggregation_method``: Defaults to ``max``. The aggregation method to use
  when retrieving measures from prometheus. Must be one of ``avg``, ``min``,
  ``max``, ``sum``, ``count``, ``stddev``, ``stdvar``.

* ``query_function``: Optional argument. The function to apply to an instant
  vector after the ``aggregation_method`` or ``range_function`` has altered the
  data. Must be one of ``abs``, ``ceil``, ``exp``, ``floor``, ``ln``, ``log2``,
  ``log10``, ``round``, ``sqrt``. For more information on these functions,
  you can check `this page`_

* ``query_prefix``: Optional argument. An arbitrary prefix to add to the
  Prometheus query generated by CloudKitty, separated by a space.

* ``query_suffix``: Optional argument. An arbitrary suffix to add to the
  Prometheus query generated by CloudKitty, separated by a space.

* ``range_function``: Optional argument. The function to apply instead of the
  implicit ``{aggregation_method}_over_time``. Must be one of ``changes``,
  ``delta``, ``deriv``, ``idelta``, ``irange``, ``irate``, ``rate``. For more
  information on these functions, you can check `this page`_

.. _this page: https://prometheus.io/docs/prometheus/latest/querying/basics/
