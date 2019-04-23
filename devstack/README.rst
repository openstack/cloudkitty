====================================
Installing CloudKitty using DevStack
====================================

The ``devstack`` directory contains the required files to integrate CloudKitty
with DevStack.

Configure DevStack to run CloudKitty
====================================

.. code-block:: bash

    $ DEVSTACK_DIR=/path/to/devstack

1. Enable Ceilometer:

   .. code-block:: bash

      $ cd ${DEVSTACK_DIR}
      $ cat >> local.conf << EOF
      [[local|localrc]]
      # ceilometer
      enable_plugin ceilometer https://opendev.org/openstack/ceilometer.git master
      EOF

2. Enable CloudKitty:

   .. code-block:: bash

      $ cd ${DEVSTACK_DIR}
      cat >> local.conf << EOF
      # cloudkitty
      enable_plugin cloudkitty https://opendev.org/openstack/cloudkitty master
      enable_service ck-api, ck-proc
      EOF

3. Set CloudKitty collector to gnocchi:

   .. code-block:: bash

      $ cd ${DEVSTACK_DIR}
      cat >> local.conf << EOF
      CLOUDKITTY_COLLECTOR=gnocchi
      EOF

Run devstack as usual:

.. code-block:: bash

     $ ./stack.sh

See the documentation_ if you want more details about how to configure the
devstack plugin.

.. _documentation: https://docs.openstack.org/cloudkitty/latest/devstack.html
