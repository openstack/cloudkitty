#####################
Devstack installation
#####################

The installation of CloudKitty from devstack is pretty straightforward. Just
add these two lines to your local.conf file.

::

    enable_plugin cloudkitty https://github.com/stackforge/cloudkitty master
    enable_service ck-api ck-proc
