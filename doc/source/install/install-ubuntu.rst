Install from packages for Ubuntu (16.04)
========================================

Packages for Ubuntu 16.04 are available starting from the Newton release.

#. Enable the OpenStack repository for the Newton or Ocata release::

    apt install software-properties-common
    add-apt-repository ppa:objectif-libre/cloudkitty # Newton
    add-apt-repository ppa:objectif-libre/cloudkitty-ocata # Ocata

#. Upgrade the packages on your host::

    apt update && apt dist-upgrade

#. Install the packages::

    apt-get install cloudkitty-api cloudkitty-processor cloudkitty-dashboard
