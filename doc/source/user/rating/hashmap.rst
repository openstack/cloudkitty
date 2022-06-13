=====================
Hashmap rating module
=====================

CloudKitty is shipped with core rating modules.

Hashmap composition
===================

HashMap is composed of different resources and groups.

Group
-----

A group is a way to group calculations of mappings. For example you might want
to apply a set of rules to rate instance uptime and another set to block
storage volume. You don't want the two to be linked so you'll create one group
for each calculation.

See **mappings** for information about how groups impact rating.

Service
-------

A service is a way to map a rule to the type of data collected. One hashmap
service must be created for each metric type you want to rate. If the metric
has an ``alt_name``, the name of the hashmap service must match the
``alt_name``. If no ``alt_name`` is provided, use the name of the metric.

Example with the default configuration:

.. code-block:: yaml

   metrics:
     cpu:
       unit: instance
       alt_name: instance
     # [...]

     image.size:
       unit: MiB
     # [...]

In this case, ``cpu`` has an alt_name and ``image.size`` hasn't. Thus, the
hashmap service for the cpu metric must be called ``instance`` and the service
for images must be called ``image.size``.

Field
-----

A field is referring to a metadata field of a resource. For example on an
instance object (in the ``instance`` service), you can use the flavor to define
specific rules.

Each ``groupby`` and ``metadata`` attribute specified in the configuration can
be used for a field:

.. code-block:: yaml

   metrics:
     cpu:
       unit: instance
       alt_name: instance
       groupby:
         - id
         - project_id
       metadata:
         - flavor_id
       # [...]

     volume.size:
       unit: GiB
       groupby:
         - id
         - project_id
       metadata:
         - volume_type
       # [...]


With the configuration above, the ``instance`` service could have the following
fields:

* id
* project_id
* flavor_id

The ``volume.size`` service could have the following fields:

* id
* project_id
* volume_type

In this case, ``flavor_id`` and ``volume_type`` can be used to apply a
different pricing based on the flavor of an instance or the type of a volume.

Mapping
-------

A mapping is the final object, it's what triggers calculation, for example a
specific value of flavor on an instance.

There are two kinds of mappings: **field** and **service** mappings.

Field mappings
++++++++++++++

A field mapping is used to match the attributes/metadata of a resource. For
example, if you have three volume types on which you want to apply distinct
rating rules, you must proceed in the following way:

1. Create a hashmap service matching the name or ``alt_name`` of the
   volume metric (``volume.size`` with default gnocchi).
2. In that service, create a field with the name of the volume type metadata
   (``volume_type`` with default gnocchi).
3. In that field, create one mapping per possible value of the ``volume_type``
   metadata. Example:

   * ``SSD_gold``: 0.03
   * ``SSD_silver``: 0.02
   * ``HDD_bronze``: 0.01

Each element of the volume metric will now be based on its ``volume_type``
metadata. A 10GiB ``SSD_gold`` volume will be rated 0.3 per collect period,
a 1GiB ``HDD_bronze`` volume will be rated 0.01, a 0.5GiB ``SSD_silver`` will
be 0.01...

Service mappings
++++++++++++++++

A service mapping is not associated with a field, but directly with a service.
If a mapping is created directly on the ``volume.size`` service, each volume
will be rated based on this mapping, with no metadata-based distinction.

Flat and Rate
+++++++++++++

A mapping can have two types: ``flat`` or ``rate``. A flat mapping is simply
added to the total for a given item, whereas a rate multiplies the total. See
the examples below use cases.

.. note::

   If several flat mappings of the same group match, only the most expensive
   one is applied.

Scope
+++++

It is possible to tie a mapping to a specific scope/tenant_id.

Threshold
---------

A threshold entry is used to apply rating rules only after a specific level.
Apart from that, it works the same way as a mapping.

As for mappings, a threshold can be tied to a specific scope/project.

Cost
----
The cost option is the actual cost for the rating period. It has a precision of
28 decimal digits (on the right side of the decimal point), and 12 digits on
the left side of the decimal point (the integer part of the number).

Examples
========

Instance uptime
---------------

Apply rating rules to rate instances based on their flavor_id and uptime:

Create an ``instance_uptime_flavor_id`` group:

.. code-block:: console

    $ cloudkitty hashmap group create instance_uptime_flavor_id
    +---------------------------+--------------------------------------+
    | Name                      | Group ID                             |
    +---------------------------+--------------------------------------+
    | instance_uptime_flavor_id | 9a2ff37d-be86-4642-8b7d-567bace61f06 |
    +---------------------------+--------------------------------------+

    $ cloudkitty hashmap group list
    +---------------------------+--------------------------------------+
    | Name                      | Group ID                             |
    +---------------------------+--------------------------------------+
    | instance_uptime_flavor_id | 9a2ff37d-be86-4642-8b7d-567bace61f06 |
    +---------------------------+--------------------------------------+


Create the service matching rule:

.. code-block:: console

    $ cloudkitty hashmap service create instance
    +----------+--------------------------------------+
    | Name     | Service ID                           |
    +----------+--------------------------------------+
    | instance | b19d801d-e7d4-46f9-970b-3e6d60fc07b5 |
    +----------+--------------------------------------+


Create a field matching rule:

.. code-block:: console

    $ cloudkitty hashmap field create b19d801d-e7d4-46f9-970b-3e6d60fc07b5 flavor_id
    +-----------+--------------------------------------+--------------------------------------+
    | Name      | Field ID                             | Service ID                           |
    +-----------+--------------------------------------+--------------------------------------+
    | flavor_id | 18aa50b6-6da8-4c47-8a1f-43236b971625 | b19d801d-e7d4-46f9-970b-3e6d60fc07b5 |
    +-----------+--------------------------------------+--------------------------------------+


Create a mapping in the ``instance_uptime_flavor`` group that will map m1.tiny
instance to a cost of 0.01:

.. code-block:: console

    $ openstack flavor show m1.tiny
    +----------------------------+----------------------------------------+
    | Field                      | Value                                  |
    +----------------------------+----------------------------------------+
    | OS-FLV-DISABLED:disabled   | False                                  |
    | OS-FLV-EXT-DATA:ephemeral  | 0                                      |
    | access_project_ids         | None                                   |
    | disk                       | 20                                     |
    | id                         | 93195dd4-bbf3-4b13-929d-8293ae72e056   |
    | name                       | m1.tiny                                |
    | os-flavor-access:is_public | True                                   |
    | properties                 | baremetal='false', flavor-type='small' |
    | ram                        | 512                                    |
    | rxtx_factor                | 1.0                                    |
    | swap                       |                                        |
    | vcpus                      | 1                                      |
    +----------------------------+----------------------------------------+

    $ cloudkitty hashmap mapping create 0.01 \
     --field-id 18aa50b6-6da8-4c47-8a1f-43236b971625 \
     --value 93195dd4-bbf3-4b13-929d-8293ae72e056 \
     -g 9a2ff37d-be86-4642-8b7d-567bace61f06 \
     -t flat
    +--------------------------------------+--------------------------------------+------------+------+--------------------------------------+------------+--------------------------------------+------------+
    | Mapping ID                           | Value                                | Cost       | Type | Field ID                             | Service ID | Group ID                             | Project ID |
    +--------------------------------------+--------------------------------------+------------+------+--------------------------------------+------------+--------------------------------------+------------+
    | 9c2418dc-99d3-44b6-8fdf-e9fa02f3ceb5 | 93195dd4-bbf3-4b13-929d-8293ae72e056 | 0.01000000 | flat | 18aa50b6-6da8-4c47-8a1f-43236b971625 | None       | 9a2ff37d-be86-4642-8b7d-567bace61f06 | None       |
    +--------------------------------------+--------------------------------------+------------+------+--------------------------------------+------------+--------------------------------------+------------+


In this example every machine in any project with the flavor m1.tiny will be
rated 0.01 per collection period.


Volume per GiB with discount
----------------------------

Now let's do some threshold based rating.

Create a ``volume_thresholds`` group:

.. code-block:: console

    $ cloudkitty hashmap group create volume_thresholds
    +-------------------+--------------------------------------+
    | Name              | Group ID                             |
    +-------------------+--------------------------------------+
    | volume_thresholds | 9736bbc0-8888-4700-96fc-58db5fded493 |
    +-------------------+--------------------------------------+

    $ cloudkitty hashmap group list
    +-------------------+--------------------------------------+
    | Name              | Group ID                             |
    +-------------------+--------------------------------------+
    | volume_thresholds | 9736bbc0-8888-4700-96fc-58db5fded493 |
    +-------------------+--------------------------------------+

Create the service matching rule:

.. code-block:: console

    $ cloudkitty hashmap service create volume.size
    +-------------+--------------------------------------+
    | Name        | Service ID                           |
    +-------------+--------------------------------------+
    | volume.size | 74ad7e4e-9cae-45a8-884b-368a92803afe |
    +-------------+--------------------------------------+


Now let's setup the price per gigabyte:

.. code-block:: console

    $ cloudkitty hashmap mapping create 0.001 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t flat -g 9736bbc0-8888-4700-96fc-58db5fded493
    +--------------------------------------+-------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | Mapping ID                           | Value | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID |
    +--------------------------------------+-------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | 09e36b13-ce89-4bd0-bbf1-1b80577031e8 | None  | 0.00100000 | flat | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | None       |
    +--------------------------------------+-------+------------+------+----------+--------------------------------------+--------------------------------------+------------+


We have the basic price per gigabyte be we now want to apply a discount on huge
data volumes. Create the thresholds in the group *volume_thresholds* that will
map different volume quantities to costs:

Here we set a threshold when going past 50GiB, and apply a 2% discount (0.98):

.. code-block:: console

    $ cloudkitty hashmap threshold create 50 0.98 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t rate -g 9736bbc0-8888-4700-96fc-58db5fded493
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | Threshold ID                         | Level       | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | ae02175d-beff-4b01-bb3a-00907b05fe66 | 50.00000000 | 0.98000000 | rate | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | None       |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+

Here we set the same threshold for project 2d5b39657dc542d4b2a14b685335304e
but with a 3% discount (0.97):

.. code-block:: console

    $ cloudkitty hashmap threshold create 50 0.97 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t rate -g 9736bbc0-8888-4700-96fc-58db5fded493 \
     -p 2d5b39657dc542d4b2a14b685335304e
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+
    | Threshold ID                         | Level       | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID                       |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+
    | b20504bf-da34-434c-909d-46c2168c6166 | 50.00000000 | 0.97000000 | rate | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | 2d5b39657dc542d4b2a14b685335304e |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+

Here we set a threshold when going past 200GiB, and apply a 5% discount (0.95):

.. code-block:: console

    $ cloudkitty hashmap threshold create 200 0.95 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t rate -g 9736bbc0-8888-4700-96fc-58db5fded493
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | Threshold ID                         | Level        | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID |
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | ed9fd297-37d4-4d9c-8f65-9919d554617b | 200.00000000 | 0.95000000 | rate | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | None       |
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+


In this example every volume is rated 0.001 per GiB but if the size goes past
50GiB you'll get a 2% discount, if you even go further you'll get 5% discount
(only one level apply at a time).

For project 2d5b39657dc542d4b2a14b685335304e only, you'll get a 3% discount
instead of 2% when the size goes past 50GiB and the same %5 discount it goes
further.

:20GiB: 0.02 per collection period.
:50GiB: 0.049 per collection period
    (0.0485 for project 2d5b39657dc542d4b2a14b685335304e).
:80GiB: 0.0784 per collection period
    (0.0776 for project 2d5b39657dc542d4b2a14b685335304e).
:250GiB: 0.2375 per collection period.
