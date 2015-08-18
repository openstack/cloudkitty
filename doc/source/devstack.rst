#####################
Devstack installation
#####################

The installation of CloudKitty from devstack is pretty straightforward. Just
add the following lines to your local.conf file.

::

    [[local|localrc]]
    # ceilometer
    enable_service ceilometer-acompute ceilometer-acentral ceilometer-anotification ceilometer-collector
    enable_service ceilometer-alarm-notifier ceilometer-alarm-evaluator
    enable_service ceilometer-api

    # horizon
    enable_service horizon

    # cloudkitty
    enable_plugin cloudkitty https://github.com/stackforge/cloudkitty master
    enable_service ck-api ck-proc
