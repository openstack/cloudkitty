#####################
DevStack installation
#####################

The installation of CloudKitty from DevStack is pretty straightforward. Just
add the following lines to your local.conf file.

::

    [[local|localrc]]
    # ceilometer
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer.git master

    # horizon
    enable_service horizon

    # cloudkitty
    enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty.git master
    enable_service ck-api ck-proc

Then, you can start devstack.

::

    ./stack.sh
