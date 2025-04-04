Install from packages for Debian
================================

Packages for Debian are available since CloudKitty 6.0.0 (OpenStack Pike) in
2018.

Optional: enable the OpenStack repository for a specific release
----------------------------------------------------------------

If using Debian Stable, and do not wish to install unofficial backports from
osbpo.debian.net, skip this step. Otherwise, here is how to enable the
repository:

.. code-block:: console

   apt-get install extrepo
   extrepo search openstack
   extrepo enable openstack_epoxy
   apt-get update

Note that it is possible to use a local mirror, and avoid internet access, by
using the extrepo-offline-data package:

.. code-block:: console

   apt-get install extrepo-offline-data
   extrepo search openstack --offlinedata
   extrepo enable openstack_epoxy --offlinedata --mirror YOUR_MIRROR

Note that extrepo-offline-data may be lagging behind the online data and it may
not contain the latest OpenStack repositories.

Upgrade the packages on your host
---------------------------------

.. code-block:: console

   apt update && apt dist-upgrade

Install the packages
--------------------

.. code-block:: console

   apt-get install cloudkitty-api cloudkitty-processor cloudkitty-dashboard
