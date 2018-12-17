..
      Copyright 2013 New Dream Network, LLC (DreamHost)

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _mod_wsgi:

==================================
Installing the API behind mod_wsgi
==================================

Cloudkitty comes with a few example files for configuring the API
service to run behind Apache with ``mod_wsgi``.

app.wsgi
========

The file ``cloudkitty/api/app.wsgi`` sets up the V1 API WSGI
application. The file needs to be copied to ``/var/www/cloudkitty/``,
and should not need to be modified.

etc/apache2/cloudkitty
======================

The ``etc/apache2/cloudkitty`` file contains example settings that
work with a copy of cloudkitty installed via devstack.

.. literalinclude:: ../../../../etc/apache2/cloudkitty

1. On deb-based systems copy or symlink the file to
   ``/etc/apache2/sites-available``. For rpm-based systems the file will go in
   ``/etc/httpd/conf.d``.

2. Modify the ``WSGIDaemonProcess`` directive to set the ``user`` and
   ``group`` values to an appropriate user on your server. In many
   installations ``cloudkitty`` will be correct.

3. Enable the cloudkitty site. On deb-based systems::

      # a2ensite cloudkitty
      # service apache2 reload

   On rpm-based systems::

      # service httpd reload
