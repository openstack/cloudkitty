#####################
DevStack installation
#####################

Add the following lines in your ``local.conf`` file to enable CloudKitty with
the ceilometer collector:

::

    [[local|localrc]]
    # ceilometer
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer.git master

    # cloudkitty
    enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty.git master
    enable_service ck-api,ck-proc
    CLOUDKITTY_COLLECTOR=ceilometer


To enable the gnocchi collector, use the following instead:

::

    [[local|localrc]]
    # gnocchi
    enable_plugin gnocchi https://github.com/gnocchixyz/gnocchi.git master
    enable_service gnocchi-api,gnocchi-metricd

    # ceilometer
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer.git master

    # cloudkitty
    enable_plugin cloudkitty https://git.openstack.org/openstack/cloudkitty.git master
    enable_service ck-api,ck-proc
    CLOUDKITTY_COLLECTOR=gnocchi


Then start devstack:

::

    ./stack.sh
