=====================
Hashmap rating module
=====================

CloudKitty is shipped with core rating modules.

Hashmap composition
===================

You can see hashmap as a simple tree:

.. graphviz:: graph/hashmap.dot


HashMap is composed of different resources and groups.

Group
-----

A group is a way to group calculations of mappings. For example you might want
to apply a set of rules to charge instance_uptime and another set to block
storage volume. You don't want the two to be linked so you'll create one group
for each calculation.

Service
-------

A service is a way to map the rule to the type of data collected. Currently,
the following services are available:

* compute
* image
* volume
* network.bw.in
* network.bw.out
* network.floating
* radosgw.usage

Enabled services are defined in the configuration file. By default, only the
compute service is enabled.

Field
-----

A field is referring to a metadata field of a resource. For example on an
instance object (**compute**), you can use the flavor to define specific rules.

With Gnocchi as collector, the following fields are available for each service:

* Compute: flavor_id, vcpus, image_id, memory (MB)
* Image: container_format, disk_format

Mapping
-------

A mapping is the final object, it's what triggers calculation, for example a
specific value of flavor on an instance.
It maps cost to a value of metadata in case of field mapping. And directly a
cost in case of service mapping.

A mapping can be project specific by providing a project id at creation and
supports overloading, i.e. you can specify multiple mappings for the same value
with different project ids and costs.

Threshold
---------

A threshold entry is used to apply rating rules base on level. Its behaviour is
similar to a mapping except that it applies the cost base on the level.

As for mapping, a threshold can be project specific by providing a project id
at creation.

HashMap formula
===============

Based on all the previous objects here's the calculation formula :
:math:`\sum_{n=1}^N G_n(qty.(T_{rate}\prod(M_{rate})(T_{flat}+M_{flat})))`

:G: Group
:qty: Quantity of resource
:T: Threshold
:M: Mapping


For an active resource on a collection period, quantity is defined as follow:

* compute: 1 (unit: instance)
* image: upload image size (unit: MB)
* volume: volume size (unit: GB)
* network.bw.in: ingoing network usage (unit: MB)
* network.bw.out: outgoing network usage (unit: MB)
* network.floating: 1 (unit: ip)
* radosgw.usage: Ceph object storage usage (unit: GB)

Example
=======

Compute uptime
--------------

Apply rating rule on the compute service to charge the instance based on it's
flavor and uptime:

Create a group *instance_uptime_flavor*:

.. code:: raw

    $ cloudkitty hashmap group create instance_uptime_flavor
    +------------------------+--------------------------------------+
    | Name                   | Group ID                             |
    +------------------------+--------------------------------------+
    | instance_uptime_flavor | 9a2ff37d-be86-4642-8b7d-567bace61f06 |
    +------------------------+--------------------------------------+

    $ cloudkitty hashmap group list
    +------------------------+--------------------------------------+
    | Name                   | Group ID                             |
    +------------------------+--------------------------------------+
    | instance_uptime_flavor | 9a2ff37d-be86-4642-8b7d-567bace61f06 |
    +------------------------+--------------------------------------+


Create the service matching rule:

.. code:: raw

    $ cloudkitty hashmap service create compute
    +---------+--------------------------------------+
    | Name    | Service ID                           |
    +---------+--------------------------------------+
    | compute | b19d801d-e7d4-46f9-970b-3e6d60fc07b5 |
    +---------+--------------------------------------+


Create a field matching rule:

.. code:: raw

    $ cloudkitty hashmap field create b19d801d-e7d4-46f9-970b-3e6d60fc07b5 flavor
    +--------+--------------------------------------+--------------------------------------+
    | Name   | Field ID                             | Service ID                           |
    +--------+--------------------------------------+--------------------------------------+
    | flavor | 18aa50b6-6da8-4c47-8a1f-43236b971625 | b19d801d-e7d4-46f9-970b-3e6d60fc07b5 |
    +--------+--------------------------------------+--------------------------------------+


Create a mapping in the group *instance_uptime_flavor* that will map m1.tiny
instance to a cost of 0.01:

.. code:: raw

    $ cloudkitty hashmap mapping create 0.01 \
     --field-id 18aa50b6-6da8-4c47-8a1f-43236b971625 \
     --value m1.tiny -t flat -g 9a2ff37d-be86-4642-8b7d-567bace61f06
    +--------------------------------------+---------+------------+------+--------------------------------------+------------+--------------------------------------+------------+
    | Mapping ID                           | Value   | Cost       | Type | Field ID                             | Service ID | Group ID                             | Project ID |
    +--------------------------------------+---------+------------+------+--------------------------------------+------------+--------------------------------------+------------+
    | 9c2418dc-99d3-44b6-8fdf-e9fa02f3ceb5 | m1.tiny | 0.01000000 | flat | 18aa50b6-6da8-4c47-8a1f-43236b971625 | None       | 9a2ff37d-be86-4642-8b7d-567bace61f06 | None       |
    +--------------------------------------+---------+------------+------+--------------------------------------+------------+--------------------------------------+------------+


In this example every machine in any project with the flavor m1.tiny will be
charged 0.01 per collection period.


Volume per gb with discount
---------------------------

Now let's do some threshold based rating.

Create a group *volume_thresholds*:

.. code:: raw

    $ cloudkitty hashmap group create volume_thresholds
    +-------------------+--------------------------------------+
    | Name              | Group ID                             |
    +-------------------+--------------------------------------+
    | volume_thresholds | 9736bbc0-8888-4700-96fc-58db5fded493 |
    +-------------------+--------------------------------------+

    $ cloudkitty hashmap group list
    +------------------------+--------------------------------------+
    | Name                   | Group ID                             |
    +------------------------+--------------------------------------+
    | volume_thresholds      | 9736bbc0-8888-4700-96fc-58db5fded493 |
    +------------------------+--------------------------------------+


Create the service matching rule:

.. code:: raw

    $ cloudkitty hashmap service create volume
    +--------+--------------------------------------+
    | Name   | Service ID                           |
    +--------+--------------------------------------+
    | volume | 74ad7e4e-9cae-45a8-884b-368a92803afe |
    +--------+--------------------------------------+


Now let's setup the price per gigabyte:

.. code:: raw

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
map different volume quantity to costs:

Here we set a threshold when going past 50GB, and apply a 2% discount (0.98):

.. code:: raw

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

.. code:: raw

    $ cloudkitty hashmap threshold create 50 0.97 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t rate -g 9736bbc0-8888-4700-96fc-58db5fded493 \
     -p 2d5b39657dc542d4b2a14b685335304e
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+
    | Threshold ID                         | Level       | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID                       |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+
    | b20504bf-da34-434c-909d-46c2168c6166 | 50.00000000 | 0.97000000 | rate | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | 2d5b39657dc542d4b2a14b685335304e |
    +--------------------------------------+-------------+------------+------+----------+--------------------------------------+--------------------------------------+----------------------------------+

Here we set a threshold when going past 200GB, and apply a 5% discount (0.95):

.. code:: raw

    $ cloudkitty hashmap threshold create 200 0.95 \
     -s 74ad7e4e-9cae-45a8-884b-368a92803afe \
     -t rate -g 9736bbc0-8888-4700-96fc-58db5fded493
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | Threshold ID                         | Level        | Cost       | Type | Field ID | Service ID                           | Group ID                             | Project ID |
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+
    | ed9fd297-37d4-4d9c-8f65-9919d554617b | 200.00000000 | 0.95000000 | rate | None     | 74ad7e4e-9cae-45a8-884b-368a92803afe | 9736bbc0-8888-4700-96fc-58db5fded493 | None       |
    +--------------------------------------+--------------+------------+------+----------+--------------------------------------+--------------------------------------+------------+


In this example every volume is charged 0.001 per GB but if the size goes past
50GB you'll get a 2% discount, if you even go further you'll get 5% discount
(only one level apply at a time).

For project 2d5b39657dc542d4b2a14b685335304e only, you'll get a 3% discount
instead of 2% when the size goes past 50GB and the same %5 discount it goes
further.

:20GB: 0.02 per collection period.
:50GB: 0.049 per collection period
    (0.0485 for project 2d5b39657dc542d4b2a14b685335304e).
:80GB: 0.0784 per collection period
    (0.0776 for project 2d5b39657dc542d4b2a14b685335304e).
:250GB: 0.2375 per collection period.
