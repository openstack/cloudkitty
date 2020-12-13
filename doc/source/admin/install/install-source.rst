Install from source
===================

Install the services
--------------------

Retrieve and install cloudkitty::

    git clone https://opendev.org/openstack/cloudkitty.git
    cd cloudkitty
    python setup.py install

This procedure installs the ``cloudkitty`` python library and the
following executables:

* ``cloudkitty-api``: API service
* ``cloudkitty-processor``: Processing service (collecting and rating)
* ``cloudkitty-dbsync``: Tool to create and upgrade the database schema
* ``cloudkitty-storage-init``: Tool to initiate the storage backend
* ``cloudkitty-writer``: Reporting tool

Install sample configuration files::

    mkdir /etc/cloudkitty
    tox -e genconfig
    cp etc/cloudkitty/cloudkitty.conf.sample /etc/cloudkitty/cloudkitty.conf
    cp etc/cloudkitty/policy.yaml /etc/cloudkitty
    cp etc/cloudkitty/api_paste.ini /etc/cloudkitty

Create the log directory::

    mkdir /var/log/cloudkitty/

Install the client
------------------

Retrieve and install cloudkitty client::

    git clone https://opendev.org/openstack/python-cloudkittyclient.git
    cd python-cloudkittyclient
    python setup.py install

Install the dashboard module
----------------------------

#. Retrieve and install cloudkitty's dashboard::

    git clone https://opendev.org/openstack/cloudkitty-dashboard.git
    cd cloudkitty-dashboard
    python setup.py install

#. Find where the python packages are installed::

    PY_PACKAGES_PATH=`pip --version | cut -d' ' -f4`

#. Add the enabled file to the horizon settings or installation.
   Depending on your setup, you might need to add it to ``/usr/share`` or
   directly in the horizon python package::

    # If horizon is installed by packages:
    ln -sf $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    /usr/share/openstack-dashboard/openstack_dashboard/enabled/

    # Directly from sources:
    ln -sf $PY_PACKAGES_PATH/cloudkittydashboard/enabled/_[0-9]*.py \
    $PY_PACKAGES_PATH/openstack_dashboard/enabled/

#. Restart the web server hosting Horizon.
