======================
 Fetcher configuration
======================

Backend option
==============

``backend`` is a common option specified in the ``[fetcher]`` section of
the configuration file. It defaults to ``keystone`` and specifies the driver
to be used for fetching the list of scopes to rate.

Fetcher-specific options
========================

Fetcher-specific options must be specified in the
``fetcher_{fetcher_name}`` section of ``cloudkitty.conf``.

Gnocchi
-------

Section ``fetcher_gnocchi``.

* ``scope_attribute``: Defaults to ``project_id``. Attribute from which
  scope_ids should be collected.

* ``resource_types``: Defaults to ``[generic]``. List of gnocchi resource
  types. All if left blank.

* ``gnocchi_auth_type``: Defaults to ``keystone``. Defines what authentication
  method should be used by the gnocchi fetcher. Must be one of ``basic``
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


Keystone
--------

Section ``fetcher_keystone``.

* ``keystone_version``: Defaults to ``3``. Keystone version to use.

* ``auth_section``: If the ``auth_section`` option is defined then all the
  options declared in the target section will be used in order to fetch scopes
  through Keystone service.

If ``auth_section`` option is not defined then you can configure Keystone
fetcher using regular Keystone authentication options as found here:
:doc:`configuration`.

* ``ignore_rating_role``: if set to true, the Keystone fetcher will not check
  if a project has the rating role; thus, CloudKitty will execute rating for
  every project it finds. Defaults to false.

* ``ignore_disabled_tenants``: if set to true, Cloudkitty will not rate
  projects that are disabled in Keystone. Defaults to false.


Prometheus
----------

Section ``fetcher_prometheus``.

* ``metric``: Metric from which scope_ids should be requested.

* ``scope_attribute``: Defaults to ``project_id``. Attribute from which
  scope_ids should be requested.

* ``filters``: Optional key-value dictionary to use additional metadata to
  filter out some of the Prometheus service response.

* ``prometheus_url``: Prometheus HTTP API URL.

* ``prometheus_user``: For HTTP basic authentication. The username.

* ``prometheus_password``: For HTTP basic authentication. The password.

* ``cafile``: Option to allow custom certificate authority file.

* ``insecure``: Option to explicitly allow untrusted HTTPS connections.

Source
------

Section ``fetcher_source``.

* ``sources``: Explicit list of scope_ids.
