DevStack installation
=====================

Add the following lines in your ``local.conf`` file to enable CloudKitty,
Ceilometer and Gnocchi. By default, the fetcher will be ``gnocchi``
(configurable via the ``CLOUDKITTY_FETCHER`` variable), the collector will be
``gnocchi`` (configurable via the ``CLOUDKITTY_COLLECTOR`` variable), and the
storage backend will be ``influxdb`` (configurable via the
``CLOUDKITTY_STORAGE_BACKEND`` and ``CLOUDKITTY_STORAGE_VERSION`` variables).

.. code-block:: ini

    [[local|localrc]]
    # ceilometer
    enable_plugin ceilometer https://opendev.org/openstack/ceilometer.git master

    # cloudkitty
    enable_plugin cloudkitty https://opendev.org/openstack/cloudkitty.git master
    enable_service ck-api,ck-proc

Then start devstack:

.. code-block:: console

    ./stack.sh
