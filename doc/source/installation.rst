#########################################
CloudKitty installation and configuration
#########################################


Install from source
===================

There is no release of CloudKitty as of now, the installation can be done from
the git repository.

Retrieve and install CloudKitty:

::

    git clone git://git.openstack.org/openstack/cloudkitty
    cd cloudkitty
    python setup.py install

This procedure installs the ``cloudkitty`` python library and a few
executables:

* ``cloudkitty-api``: API service
* ``cloudkitty-processor``: Processing service (collecting and rating)
* ``cloudkitty-dbsync``: Tool to create and upgrade the database schema
* ``cloudkitty-storage-init``: Tool to initiate the storage backend
* ``cloudkitty-writer``: Reporting tool

Install sample configuration files:

::

    mkdir /etc/cloudkitty
    cp etc/cloudkitty/cloudkitty.conf.sample /etc/cloudkitty/cloudkitty.conf
    cp etc/cloudkitty/policy.json /etc/cloudkitty

Install from packages
=====================

Packages for RHEL/CentOS 7 and Ubuntu 14.04 are available for the Kilo release.

For RHEL/CentOS 7
-----------------

#. Enable the EPEL and RDO repositories for Kilo:

::

    yum install https://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
    yum install http://rdo.fedorapeople.org/openstack-kilo/rdo-release-kilo.rpm

#. Create the ``/etc/yum.repos.d/cloudkitty.repo`` configuration file to enable
   the CloudKitty repository:

.. code-block:: ini

    [cloudkitty]
    name=CloudKitty repository (Kilo)
    baseurl=http://archive.objectif-libre.com/cloudkitty/el7/kilo/
    gpgcheck=1
    gpgkey=http://archive.objectif-libre.com/ol.asc

#. Install the packages:

::

    yum install cloudkitty-api cloudkitty-processor cloudkitty-dashboard


For Ubuntu 14.04
----------------

#. Enable the Canonical cloud-archive repository for the Kilo release:

::

    apt-get install ubuntu-cloud-keyring
    echo "deb http://ubuntu-cloud.archive.canonical.com/ubuntu trusty-updates/kilo main" > \
        /etc/apt/sources.list.d/cloudarchive-kilo.list


#. Install the CloudKitty repository public key and configure apt:

::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 71E414B3
    echo 'deb http://archive.objectif-libre.com/cloudkitty/ubuntu trusty/kilo main' > \
        /etc/apt/sources.list.d/cloudkitty-kilo.list
    apt-get update

#. Install the packages:

::

    apt-get install cloudkitty-api cloudkitty-processor cloudkitty-dashboard


Configure CloudKitty
====================

Edit :file:`/etc/cloudkitty/cloudkitty.conf` to configure CloudKitty.

The following shows the basic configuration items:

.. code-block:: ini

    [DEFAULT]
    verbose = True
    log_dir = /var/log/cloudkitty

    [oslo_messaging_rabbit]
    rabbit_userid = openstack
    rabbit_password = RABBIT_PASSWORD
    rabbit_hosts = RABBIT_HOST

    [auth]
    username = cloudkitty
    password = CK_PASSWORD
    tenant = service
    region = RegionOne
    url = http://localhost:5000/v2.0

    [keystone_authtoken]
    username = cloudkitty
    password = CK_PASSWORD
    project_name = service
    region = RegionOne
    auth_url = http://localhost:5000/v2.0
    auth_plugin = password

    [database]
    connection = mysql://cloudkitty:CK_DBPASS@localhost/cloudkitty

    [keystone_fetcher]
    username = admin
    password = ADMIN_PASSWORD
    tenant = admin
    region = RegionOne
    url = http://localhost:5000/v2.0

    [ceilometer_collector]
    username = cloudkitty
    password = CK_PASSWORD
    tenant = service
    region = RegionOne
    url = http://localhost:5000


Setup the database and storage backend
======================================

MySQL/MariaDB is the recommended database engine. To setup the database, use
the ``mysql`` client:

::

    mysql -uroot -p << EOF
    CREATE DATABASE cloudkitty;
    GRANT ALL PRIVILEGES ON cloudkitty.* TO 'cloudkitty'@'localhost' IDENTIFIED BY 'CK_DBPASS';
    EOF


Run the database synchronisation scripts:

::

    cloudkitty-dbsync upgrade


Init the storage backend:

::

    cloudkitty-storage-init


Setup Keystone
==============

CloudKitty uses Keystone for authentication, and provides a ``rating`` service.

To integrate CloudKitty to Keystone, run the following commands (as OpenStack
administrator):

::

    keystone user-create --name cloudkitty --pass CK_PASS
    keystone user-role-add --user cloudkitty --role admin --tenant service


Give the ``rating`` role to ``cloudkitty`` for each tenant that should be
handled by CloudKitty:

::

    keystone role-create --name rating
    keystone user-role-add --user cloudkitty --role rating --tenant XXX


Create the ``rating`` service and its endpoints:

::

    keystone service-create --name CloudKitty --type rating
    keystone endpoint-create --service-id RATING_SERVICE_ID \
        --publicurl http://localhost:8888 \
        --adminurl http://localhost:8888 \
        --internalurl http://localhost:8888

Start CloudKitty
================

Start the API and processing services:

::

    cloudkitty-api --config-file /etc/cloudkitty/cloudkitty.conf
    cloudkitty-processor --config-file /etc/cloudkitty/cloudkitty.conf


Horizon integration
===================

Retrieve and install CloudKitty's dashboard:

::

    git clone git://git.openstack.org/openstack/cloudkitty-dashboard
    cd cloudkitty-dashboard
    python setup.py install


Find where the python packages are installed:

::

    PY_PACKAGES_PATH=`pip --version | cut -d' ' -f4`


Then add the enabled file to the horizon settings or installation. Depending on
your setup, you might need to add it to ``/usr/share`` or directly in the
horizon python package:

::

    # If horizon is installed by packages:
    ln -s $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    /usr/share/openstack-dashboard/openstack_dashboard/enabled/

    # Directly from sources:
    ln -s $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    $PY_PACKAGES_PATH/openstack_dashboard/enabled/


Restart the web server hosting Horizon.
