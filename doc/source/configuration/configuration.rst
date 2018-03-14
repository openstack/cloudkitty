###################
Configuration Guide
###################

Configure Cloudkitty
====================

Edit :file:`/etc/cloudkitty/cloudkitty.conf` to configure cloudkitty.

Then you need to know which keystone API version you use (which can be
determined using ``openstack endpoint list``)


The first thing to set is the authentication method wished to reach Cloudkitty
API endpoints.


Without authentication
----------------------

If wanted, you can choose to not set any authentication method.
This should be set in the ``DEFAULT`` block of the configuration file owing to
the ``auth_strategy`` field:

.. code-block:: ini

    [DEFAULT]
    verbose = True
    log_dir = /var/log/cloudkitty
    # oslo_messaging_rabbit is deprecated
    transport_url = rabbit://RABBIT_USER:RABBIT_PASSWORD@RABBIT_HOST
    auth_strategy = noauth


Otherwise, the only other officially implemented authentication method is
keystone. More methods will be implemented soon. It should be set in the
``DEFAULT`` configuration block too, with the ``auth_stategy`` field.


For keystone (identity) API v2 (deprecated)
-------------------------------------------

.. code-block:: ini

    [DEFAULT]
    verbose = True
    log_dir = /var/log/cloudkitty
    # oslo_messaging_rabbit is deprecated
    transport_url = rabbit://RABBIT_USER:RABBIT_PASSWORD@RABBIT_HOST/
    auth_strategy = keystone

    [auth]
    username = cloudkitty
    password = CK_PASSWORD
    tenant = service
    region = RegionOne
    url = http://KEYSTONE_HOST:5000/v2.0

    [keystone_authtoken]
    username = cloudkitty
    password = CK_PASSWORD
    project_name = service
    region = RegionOne
    auth_url = http://KEYSTONE_HOST:5000/v2.0
    auth_plugin = password

    [database]
    connection = mysql+pymysql://CK_DBUSER:CK_DBPASSWORD@DB_HOST/cloudkitty

    [storage]
    backend = sqlalchemy

    [keystone_fetcher]
    username = cloudkitty
    password = CK_PASSWORD
    tenant = service
    region = RegionOne
    url = http://KEYSTONE_HOST:5000/v2.0

    [collect]
    collector = ceilometer
    period = 3600
    services = compute, volume, network.bw.in, network.bw.out, network.floating, image

    [ceilometer_collector]
    username = cloudkitty
    password = CK_PASSWORD
    tenant = service
    region = RegionOne
    url = http://KEYSTONE_HOST:5000/v2.0

.. note::

   * ``http://KEYSTONE_HOST:5000/v2.0`` and ``http://KEYSTONE_HOST:35357/v2.0`` are your
     identity endpoints.

   * the tenant named ``service`` is also commonly called ``services``

For keystone (identity) API v3
------------------------------

The following shows the basic configuration items:

.. code-block:: ini

    [DEFAULT]
    verbose = True
    log_dir = /var/log/cloudkitty
    # oslo_messaging_rabbit is deprecated
    transport_url = rabbit://RABBIT_USER:RABBIT_PASSWORD@RABBIT_HOST/
    auth_strategy = keystone

    [ks_auth]
    auth_type = v3password
    auth_protocol = http
    auth_url = http://KEYSTONE_HOST:5000/
    identity_uri = http://KEYSTONE_HOST:35357/
    username = cloudkitty
    password = CK_PASSWORD
    project_name = service
    user_domain_name = default
    project_domain_name = default
    debug = True

    [keystone_authtoken]
    auth_section = ks_auth

    [database]
    connection = mysql+pymysql://CK_DBUSER:CK_DBPASSWORD@DB_HOST/cloudkitty

    [keystone_fetcher]
    auth_section = ks_auth
    keystone_version = 3

    [tenant_fetcher]
    backend = keystone

.. note::

   The tenant named ``service`` is also commonly called ``services``

It is now time to configure the storage backend. Two storage backends are
available: ``sqlalchemy`` and ``hybrid`` (which will soon become the v2
storage).

.. code-block:: ini

   [storage]
   backend = hybrid

As you will see in the following example, collector and storage backends
sometimes need additional configuration sections. (The tenant fetcher works the
same way). The section's name has the following format:
``{backend_name}_{backend_type}`` (``gnocchi_collector`` for example), except
for ``storage_gnocchi``.

.. note::

   The section name format should become ``{backend_type}_{backend_name}`` for
   all sections in the future (``storage_gnocchi`` style).

If you want to use the hybrid storage with a gnocchi backend, add the following
entry:

.. code-block:: ini

   [storage_gnocchi]
   auth_section = ks_auth

Two collectors are available: Gnocchi and Monasca. The Monasca collector
collects metrics published by the Ceilometer agent to Monasca using Ceilosca_.

The collect information, is separated from the Cloudkitty configuration file,
in a yaml one.

This allows Cloudkitty users to change metrology configuration,
without modifying source code or Cloudkitty configuration file.

.. code-block:: ini

    [collect]
    metrics_conf = /etc/cloudkitty/metrics.yml

    [gnocchi_collector]
    auth_section = ks_auth

The ``/etc/cloudkitty/metrics.yml`` file looks like this:

.. literalinclude:: ../../../etc/cloudkitty/metrics.yml
   :language: yaml

Conversion information is included in the yaml file.
It allows operators to change metrics units for rating
and so to not stay stuck with the original unit.

The conversion information must be set for each metric.
It includes optionals factor and offset,
plus a mandatory final unit (used once the conversion is done).
By default, factor and offset are 1 and 0 respectively.
All type of linear conversions are so covered.
The complete formula looks like:

``new_value = (value * factor) + offset``


Setup the database and storage backend
--------------------------------------

MySQL/MariaDB is the recommended database engine. To setup the database, use
the ``mysql`` client::

    mysql -uroot -p << EOF
    CREATE DATABASE cloudkitty;
    GRANT ALL PRIVILEGES ON cloudkitty.* TO 'CK_DBUSER'@'localhost' IDENTIFIED BY 'CK_DBPASSWORD';
    EOF

If you need to authorize the mysql user associated to cloudkitty from another host you
have to change the line accordingly.

Run the database synchronisation scripts::

    cloudkitty-dbsync upgrade


Init the storage backend::

    cloudkitty-storage-init


Integration with Keystone
-------------------------

cloudkitty uses Keystone for authentication, and provides a ``rating`` service.

To integrate cloudkitty to Keystone, run the following commands (as OpenStack
administrator)::

    openstack user create cloudkitty --password CK_PASSWORD --email cloudkitty@localhost
    openstack role add --project service --user cloudkitty admin


Give the ``rating`` role to ``cloudkitty`` for each project that should be
handled by cloudkitty::

    openstack role create rating
    openstack role add --project XXX --user cloudkitty rating

Create the ``rating`` service and its endpoints::

    openstack service create rating --name cloudkitty \
        --description "OpenStack Rating Service"
    openstack endpoint create rating --region RegionOne \
        public http://localhost:8889
    openstack endpoint create rating --region RegionOne \
        admin http://localhost:8889
    openstack endpoint create rating --region RegionOne \
        internal http://localhost:8889

.. note::

    The default port for the API service changed from 8888 to 8889
    in the Newton release. If you installed Cloudkitty in an
    earlier version, make sure to either explicitly define the
    ``[api]/port`` setting to 8888 in ``cloudkitty.conf``, or update
    your keystone endpoints to use the 8889 port.

Start cloudkitty
================

If you installed cloudkitty from packages
-----------------------------------------

Start the processing services::

    systemctl start cloudkitty-processor.service

If you installed cloudkitty from sources
-----------------------------------------

Start the processing services::

    cloudkitty-processor --config-file /etc/cloudkitty/cloudkitty.conf

Choose and start the API server
-------------------------------

Cloudkitty includes the ``cloudkitty-api`` command. It can be
used to run the API server. For smaller or proof-of-concept
installations this is a reasonable choice. For larger installations it
is strongly recommended to install the API server in a WSGI host
such as mod_wsgi (see :ref:`mod_wsgi`). Doing so will provide better
performance and more options for making adjustments specific to the
installation environment.

If you are using the ``cloudkitty-api`` command it can be started as::

    $ cloudkitty-api -p 8889


.. _Ceilosca: https://github.com/openstack/monasca-ceilometer
