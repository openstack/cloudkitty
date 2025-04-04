Install from packages for Ubuntu
================================

Note that Canonical doesn't maintain CloudKitty packages. These are only
maintained in Debian, and then imported from Debian Unstable to the
Ubuntu Universe repository.

#. Upgrade the packages on your host::

    apt update && apt dist-upgrade

#. Install the packages::

    apt-get install cloudkitty-api cloudkitty-processor cloudkitty-dashboard
