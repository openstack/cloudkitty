=====================
Cloudkitty Status CLI
=====================

This chapter documents :command:`cloudkitty-status`.

For help on a specific :command:`cloudkitty-status` command, enter:

.. code-block:: console

   $ cloudkitty-status COMMAND --help

cloudkitty-status
=================

:program:`cloudkitty-status` is a tool that provides routines for checking the
status of a Cloudkitty deployment.

The standard pattern for executing a :program:`cloudkitty-status` command is:

.. code-block:: console

    cloudkitty-status <category> <command> [<args>]

Run without arguments to see a list of available command categories:

.. code-block:: console

    cloudkitty-status

Categories are:

* ``upgrade``

Detailed descriptions are below.

You can also run with a category argument such as ``upgrade`` to see a list of
all commands in that category:

.. code-block:: console

    cloudkitty-status upgrade

The following sections describe the available categories and arguments for
:program:`cloudkitty-status`.

cloudkitty-status upgrade
=========================

.. _cloudkitty-status-upgrade-check:

cloudkitty-status upgrade check
-------------------------------

``cloudkitty-status upgrade check``
  Performs a release-specific readiness check before restarting services with
  new code. This command expects to have complete configuration and access
  to the database.

  **Return Codes**

  .. list-table::
     :widths: 20 80
     :header-rows: 1

     * - Return code
       - Description
     * - 0
       - All upgrade readiness checks passed successfully and there is nothing
         to do.
     * - 1
       - At least one check encountered an issue and requires further
         investigation. This is considered a warning but the upgrade may be OK.
     * - 2
       - There was an upgrade status check failure that needs to be
         investigated. This should be considered something that stops an
         upgrade.
     * - 255
       - An unexpected error occurred.

  **History of Checks**

  **9.0.0 (Stein)**

  * Checks that the storage interface version is 2 (which is default).
