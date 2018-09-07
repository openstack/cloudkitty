Install from package (RDO For RHEL/CentOS 7)
============================================

Packages for RHEL/CentOS 7 are available starting from the Mitaka release.

#. Install the RDO repositories for your release::

    yum install centos-release-openstack-RELEASE
    # RELEASE can be any supported release name like rocky

#. Install the packages::

    yum install openstack-cloudkitty-api openstack-cloudkitty-processor openstack-cloudkitty-ui
