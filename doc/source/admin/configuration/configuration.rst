================================
Step by step configuration guide
================================

.. note:: For a sample ``cloudkitty.conf`` file, see
          :doc:`samples/cloudkitty-conf` .

Edit ``/etc/cloudkitty/cloudkitty.conf`` to configure cloudkitty.

Common options
--------------

Options supported by most OpenStack projects are also supported by cloudkitty:

.. code-block:: ini

    [DEFAULT]
    verbose = true
    debug = false
    log_dir = /var/log/cloudkitty
    transport_url = rabbit://RABBIT_USER:RABBIT_PASSWORD@RABBIT_HOST


API authentication method
-------------------------

The authentication method is defined through the ``auth_strategy`` option in
the ``[DEFAULT]`` section.

Standalone mode
+++++++++++++++

If you're using CloudKitty in standalone mode, you'll have to use noauth:

.. code-block:: ini

    [DEFAULT]
    auth_strategy = noauth

Keystone integration
++++++++++++++++++++

If you're using CloudKitty with OpenStack, you'll want to use Keystone
authentication:

.. code-block:: ini

    [DEFAULT]
    auth_strategy = keystone

When using Keystone, you'll have to provide the CloudKitty credentials for
Keystone. These must be specified in the ``[keystone_authtoken]`` section.
Since these credentials will be used in multiple places, it is convenient to
use a common section:

.. code-block:: ini

    [ks_auth]
    auth_type = v3password
    auth_protocol = http
    auth_url = http://KEYSTONE_HOST:5000/
    identity_uri = http://KEYSTONE_HOST:5000/
    username = cloudkitty
    password = CK_PASSWORD
    project_name = service
    user_domain_name = default
    project_domain_name = default

    [keystone_authtoken]
    auth_section = ks_auth

.. note:: The ``service`` project may also be called ``services``.

CloudKitty provides the ``rating`` OpenStack service.

To integrate cloudkitty to Keystone, run the following commands (as OpenStack
administrator):

.. code-block:: shell

    openstack user create cloudkitty --password CK_PASSWORD

    openstack role add --project service --user cloudkitty admin

    openstack service create rating --name cloudkitty \
        --description "OpenStack Rating Service"

    openstack endpoint create rating --region RegionOne \
        public http://localhost:8889

    openstack endpoint create rating --region RegionOne \
        admin http://localhost:8889

    openstack endpoint create rating --region RegionOne \
        internal http://localhost:8889

Storage
-------

The next step is to configure the storage. Start with the SQL and create the
``cloudkitty`` table and user:

.. code-block:: shell

    mysql -uroot -p << EOF
    CREATE DATABASE cloudkitty;
    GRANT ALL PRIVILEGES ON cloudkitty.* TO 'CK_DBUSER'@'localhost' IDENTIFIED BY 'CK_DBPASSWORD';
    EOF

Specify the SQL credentials in the ``[database]`` section of the configuration
file:

.. code-block:: ini

    [database]
    connection = mysql+pymysql://CK_DBUSER:CK_DBPASSWORD@DB_HOST/cloudkitty

Once you have set up the SQL database service, the storage backend for rated
data can be configured. A complete configuration reference can be found in the
`storage backend configuration guide`_. We'll use a v2 storage backend, which
enables the v2 API. The storage version and driver to use must be specified in
the ``[storage]`` section of the documentation:

.. code-block:: ini

   [storage]
   version = 2
   backend = influxdb

Driver-specific options are then specified in the ``[storage_{drivername}]``
section:

.. code-block:: ini

   [storage_influxdb]
   username = cloudkitty
   password = cloudkitty
   database = cloudkitty
   host = influxdb

Once you have configured the SQL and rated data storage backends, initalize
the storage::

   cloudkitty-storage-init

Then, run the database migrations::

   cloudkitty-dbsync upgrade

.. _storage backend configuration guide: ./storage.html

Fetcher
-------

The fetcher retrieves the list of scopes to rate, which will then be passed
to the collector. A complete configuration reference can be found in the
`fetcher configuration guide`_. For this example, we'll use the ``gnocchi``
fetcher, which will discover scopes (in this case OpenStack projects) to rate.
The fetcher to use is specified through the ``backend`` option of the
``[fetcher]`` section:

.. code-block:: ini

   [fetcher]
   backend = gnocchi

Fetcher-specific options are then specified in the ``[fetcher_{fetchername}]``
section:

.. code-block:: ini

   [fetcher_gnocchi]
   auth_section = ks_auth
   region_name = MyRegion

.. _fetcher configuration guide: ./fetcher.html

Collector
---------

The collector will retrieve data for the scopes provided by the fetcher and
pass them to the rating modules. The collector to use is specified in
the ``[collect]`` section, and the collector-specific options are specified
in the ``[collector_{collectorname}]`` section:

.. code-block:: ini

   [collect]
   collector = gnocchi

   [collector_gnocchi]
   auth_section = ks_auth
   region_name = MyRegion

Note that you'll also have to configure what metrics the collector should
collect, and how they should be collected. Have a look at the
`collector configuration guide`_ for this:

.. _collector configuration guide: ./collector.html
