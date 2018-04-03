====================================
Installing CloudKitty using DevStack
====================================

The ``devstack`` directory contains the required files to integrate CloudKitty
with DevStack.

Configure DevStack to run CloudKitty
====================================

    $ DEVSTACK_DIR=/path/to/devstack

1. enable Ceilometer::

   $ cd ${DEVSTACK_DIR}
   $ cat >> local.conf << EOF
   [[local|localrc]]
   # ceilometer
   enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer.git master
   EOF

2. enable CloudKitty::

   $ cd ${DEVSTACK_DIR}
   cat >> local.conf << EOF
   # cloudkitty
   enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty master
   enable_service ck-api, ck-proc
   EOF

3. Set CloudKitty collector to gnocchi::

   $ cd ${DEVSTACK_DIR}
   cat >> local.conf << EOF
   CLOUDKITTY_COLLECTOR=gnocchi
   EOF

Run devstack as usual::

    $ ./stack.sh
