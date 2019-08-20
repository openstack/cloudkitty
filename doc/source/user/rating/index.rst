======
Rating
======

CloudKitty is shipped with three rating modules:

* ``noop``: Rating module for testing purpose (enabled only).

* ``hashmap``: Default rating module corresponding to usual CloudKitty
  use cases (disabled by default).

* ``pyscripts``: Custom rating module allowing you to add your
  own python scripts (disabled by default).

You can enable or disable each module independently
and prioritize one over another at will.

* ``Enabled`` state is represented by a boolean value (``True`` or ``False``).
* ``Priority`` is represented by an integer value.

.. note::

   The module with the biggest priority value will process data first
   (descending order).

List available modules
======================

List available rating modules:

.. code-block:: console

    $ cloudkitty module list
    +-----------+---------+----------+
    | Module    | Enabled | Priority |
    +-----------+---------+----------+
    | hashmap   | False   | 1        |
    | noop      | True    | 1        |
    | pyscripts | False   | 1        |
    +-----------+---------+----------+

Enable or disable module
========================

Enable the hashmap rating module:

.. code-block:: console

    $ cloudkitty module enable hashmap
    +---------+---------+----------+
    | Module  | Enabled | Priority |
    +---------+---------+----------+
    | hashmap | True    | 1        |
    +---------+---------+----------+

Disable the pyscripts rating module:

.. code-block:: console

    $ cloudkitty module disable pyscripts
    +-----------+---------+----------+
    | Module    | Enabled | Priority |
    +-----------+---------+----------+
    | pyscripts | False   | 1        |
    +-----------+---------+----------+

Set priority
============

Set the hashmap rating module priority to 100:

.. code-block:: console

    $ cloudkitty module set priority hashmap 100
    +---------+---------+----------+
    | Module  | Enabled | Priority |
    +---------+---------+----------+
    | hashmap | True    | 100      |
    +---------+---------+----------+

More details
============
.. toctree::
   :maxdepth: 2
   :glob:

   hashmap.rst
   pyscripts.rst
