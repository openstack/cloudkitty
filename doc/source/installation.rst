#########################################
CloudKitty installation and configuration
#########################################


Install from source
===================

There is no release of CloudKitty as of now, the installation can be done from
the git repository.

Retrieve and install CloudKitty::

    git clone https://git.openstack.org/openstack/cloudkitty.git
    cd cloudkitty
    python setup.py install

This procedure installs the ``cloudkitty`` python library and a few
executables:

* ``cloudkitty-api``: API service
* ``cloudkitty-processor``: Processing service (collecting and rating)
* ``cloudkitty-dbsync``: Tool to create and upgrade the database schema
* ``cloudkitty-storage-init``: Tool to initiate the storage backend
* ``cloudkitty-writer``: Reporting tool

Install sample configuration files::

    mkdir /etc/cloudkitty
    tox -e genconfig
    cp etc/cloudkitty/cloudkitty.conf.sample /etc/cloudkitty/cloudkitty.conf
    cp etc/cloudkitty/policy.json /etc/cloudkitty
    cp etc/cloudkitty/api_paste.ini /etc/cloudkitty

Retrieve and install cloudkitty client::

    git clone https://git.openstack.org/openstack/python-cloudkittyclient.git
    cd python-cloudkittyclient
    python setup.py install


Install from packages
=====================

Packages for RHEL/CentOS 7 and Ubuntu 16.04 are available for the Newton release.

For RHEL/CentOS 7
-----------------

#. Install the RDO repositories for Newton::

    yum install -y centos-release-openstack-newton

#. Install the packages::

    yum install openstack-cloudkitty-api openstack-cloudkitty-processor openstack-cloudkitty-ui


For Ubuntu 16.04
----------------

#. Enable the OpenStack repository for the Newton release::

    apt install software-properties-common
    add-apt-repository ppa:objectif-libre/cloudkitty

#. Upgrade the packages on your host::

    apt update && apt dist-upgrade

#. Install the packages::

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
the ``mysql`` client::

    mysql -uroot -p << EOF
    CREATE DATABASE cloudkitty;
    GRANT ALL PRIVILEGES ON cloudkitty.* TO 'cloudkitty'@'localhost' IDENTIFIED BY 'CK_DBPASS';
    EOF


Run the database synchronisation scripts::

    cloudkitty-dbsync upgrade


Init the storage backend::

    cloudkitty-storage-init


Setup Keystone
==============

CloudKitty uses Keystone for authentication, and provides a ``rating`` service.

To integrate CloudKitty to Keystone, run the following commands (as OpenStack
administrator)::

    openstack user create cloudkitty --password CK_PASS --email cloudkitty@localhost
    openstack role add --project service --user cloudkitty admin


Give the ``rating`` role to ``cloudkitty`` for each project that should be
handled by CloudKitty::

    openstack role create rating
    openstack role add --project XXX --user cloudkitty rating

Create the ``rating`` service and its endpoints::

    openstack service create rating --name CloudKitty \
        --description "OpenStack Rating Service"
    openstack endpoint create rating --region RegionOne \
        --publicurl http://localhost:8889 \
        --adminurl http://localhost:8889 \
        --internalurl http://localhost:8889


Start CloudKitty
================

Start the API and processing services::

    cloudkitty-api --config-file /etc/cloudkitty/cloudkitty.conf
    cloudkitty-processor --config-file /etc/cloudkitty/cloudkitty.conf


Horizon integration from cloudkitty-dashboard source
====================================================

Retrieve and install CloudKitty's dashboard::

    git clone https://git.openstack.org/openstack/cloudkitty-dashboard.git
    cd cloudkitty-dashboard
    python setup.py install


Find where the python packages are installed::

    PY_PACKAGES_PATH=`pip --version | cut -d' ' -f4`


Then add the enabled file to the horizon settings or installation. Depending on
your setup, you might need to add it to ``/usr/share`` or directly in the
horizon python package::

    # If horizon is installed by packages:
    ln -sf $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    /usr/share/openstack-dashboard/openstack_dashboard/enabled/

    # Directly from sources:
    ln -sf $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    $PY_PACKAGES_PATH/openstack_dashboard/enabled/


Restart the web server hosting Horizon.
