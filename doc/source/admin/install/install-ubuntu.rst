Install from packages for Ubuntu
================================

Packages for Ubuntu are available since CloudKitty 7.0.0 (OpenStack Queens) in
2018.

#. Upgrade the packages on your host:

    .. code-block:: console

        apt update && apt dist-upgrade

#. Install the packages:

    .. code-block:: console

        apt-get install cloudkitty-api cloudkitty-processor cloudkitty-dashboard
