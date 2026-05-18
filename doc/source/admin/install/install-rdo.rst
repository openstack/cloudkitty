Install from package (RDO For RHEL/CentOS)
==========================================

Packages for RHEL/CentOS are available starting from the Mitaka release.

#. Install the RDO repositories for your release:

    .. code-block:: console

       dnf install centos-release-openstack-RELEASE
       # RELEASE can be any supported release name like rocky

#. Install the packages:

    .. code-block:: console

       dnf install openstack-cloudkitty-api openstack-cloudkitty-processor openstack-cloudkitty-ui
