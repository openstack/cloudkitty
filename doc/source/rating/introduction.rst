==========================
Rating module introduction
==========================

There are three rating modules in Cloudkitty now, including the ``noop``,
``hashmap`` and ``pyscripts``. Only the noop rating module is just for
testing. All modules can be enabled and disabled dynamically. Cloudkitty
allows to run several rating modules simultaneously, and the user or
operator can set the priority for a module. The order in which the modules
process the data depends on their priority. The module with the highest
priority comes first.

Enable or disable module
==========================

Enable the hashmap rating module:

.. code:: raw

    $ cloudkitty module-enable -n hashmap
    +---------+---------+----------+
    | Module  | Enabled | Priority |
    +---------+---------+----------+
    | hashmap | True    | 1        |
    +---------+---------+----------+

Disable the pyscripts rating module:

.. code:: raw

    $ cloudkitty module-disable -n pyscripts
    +-----------+---------+----------+
    | Module    | Enabled | Priority |
    +-----------+---------+----------+
    | pyscripts | False   | 1        |
    +-----------+---------+----------+

Set priority
============

Set the hashmap rating module priority to 100:

.. code:: raw

    $ cloudkitty module-set-priority -n hashmap -p 100
    +---------+---------+----------+
    | Module  | Enabled | Priority |
    +---------+---------+----------+
    | hashmap | True    | 100      |
    +---------+---------+----------+
