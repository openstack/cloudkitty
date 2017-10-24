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

    2. enable Gnocchi::

        $ cd ${DEVSTACK_DIR}
        $ cat >> local.conf << EOF
        # gnocchi
        enable_plugin gnocchi https://github.com/gnocchixyz/gnocchi
        enable_service gnocchi-api, gnocchi-metricd
        EOF

    3. enable CloudKitty::

        $ cd ${DEVSTACK_DIR}
        cat >> local.conf << EOF
        # cloudkitty
        enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty master
        enable_service ck-api, ck-proc
        EOF

Run devstack as normal::

    $ ./stack.sh
