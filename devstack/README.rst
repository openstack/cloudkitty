====================================
Installing CloudKitty using DevStack
====================================

The ``devstack`` directory contains the files necessary to integrate CloudKitty with DevStack.

Configure DevStack to run CloudKitty

    $ DEVSTACK_DIR=/path/to/devstack

    1. enable Ceilometer::

        $ cd ${DEVSTACK_DIR}
        $ cat >> local.conf << EOF
        [[local|localrc]]
        # ceilometer
        enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer.git master
        EOF

    2. enable Horizon::

        $ cd ${DEVSTACK_DIR}
        $ cat >> local.conf << EOF
        # horizon
        enable_service horizon
        EOF

    3. enable CloudKitty::

        $ cd ${DEVSTACK_DIR}
        cat >> local.conf << EOF
        # cloudkitty
        enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty master
        EOF

Run devstack as normal::

    $ ./stack.sh
