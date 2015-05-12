====================================
Installing CloudKitty using devstack
====================================

The contrib/devstack/ directory contains the files necessary to integrate CloudKitty with devstack.

Install::

    $ DEVSTACK_DIR=/path/to/devstack
    $ CLOUDKITTY_DIR=/path/to/cloudkitty
    $ cd ${CLOUDKITTY_DIR}/contrib/devstack
    $ cp lib/cloudkitty ${DEVSTACK_DIR}/lib
    $ cp extras.d/70-cloudkitty.sh ${DEVSTACK_DIR}/extras.d

Configure devstack to run CloudKitty

    1. enable Ceilometer::

        $ cd ${DEVSTACK_DIR}
        $ cat >> local.conf << EOF
        [[local|localrc]]
        # ceilometer
        enable_service ceilometer-acompute ceilometer-acentral ceilometer-anotification ceilometer-collector
        enable_service ceilometer-alarm-notifier ceilometer-alarm-evaluator
        enable_service ceilometer-api
        EOF

    2. enable CloudKitty::

        $ cd ${DEVSTACK_DIR}
        cat >> local.conf << EOF
        # cloudkitty
        enable_service ck-api ck-proc
        EOF

Run devstack as normal::

    $ ./stack.sh
