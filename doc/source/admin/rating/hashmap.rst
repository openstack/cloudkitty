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

    $ cloudkitty hashmap-group-create -n instance_uptime_flavor
    +----------+--------------------------------------+
    | Property | Value                                |
    +----------+--------------------------------------+
    | group_id | 26d2d69a-4c42-47f1-9d44-2cdfad167f7d |
    | name     | instance_uptime_flavor               |
    +----------+--------------------------------------+

    $ cloudkitty hashmap-group-list
    +------------------------+--------------------------------------+
    | Name                   | Group id                             |
    +------------------------+--------------------------------------+
    | instance_uptime_flavor | 26d2d69a-4c42-47f1-9d44-2cdfad167f7d |
    +------------------------+--------------------------------------+


Create the service matching rule:

.. code:: raw

    $ cloudkitty hashmap-service-create -n compute
    +------------+--------------------------------------+
    | Property   | Value                                |
    +------------+--------------------------------------+
    | name       | compute                              |
    | service_id | 08ab2d27-fe95-400c-9602-e5ad5efdda8b |
    +------------+--------------------------------------+


Create a field matching rule:

.. code:: raw

    $ cloudkitty hashmap-field-create \
     -s 08ab2d27-fe95-400c-9602-e5ad5efdda8b -n flavor
    +------------+--------------------------------------+
    | Property   | Value                                |
    +------------+--------------------------------------+
    | field_id   | f37364af-6525-40fc-ae08-6d4087429862 |
    | name       | flavor                               |
    | service_id | 08ab2d27-fe95-400c-9602-e5ad5efdda8b |
    +------------+--------------------------------------+


Create a mapping in the group *instance_uptime_flavor* that will map m1.tiny
instance to a cost of 0.01:

.. code:: raw

    $ cloudkitty hashmap-mapping-create \
     -f f37364af-6525-40fc-ae08-6d4087429862 \
     -v m1.tiny -t flat -c 0.01 -g 26d2d69a-4c42-47f1-9d44-2cdfad167f7d
    +------------+--------------------------------------+
    | Property   | Value                                |
    +------------+--------------------------------------+
    | cost       | 0.01                                 |
    | field_id   | f37364af-6525-40fc-ae08-6d4087429862 |
    | group_id   | 26d2d69a-4c42-47f1-9d44-2cdfad167f7d |
    | mapping_id | df592a91-a6a5-41fa-ba2e-2f763eaa36e5 |
    | service_id | None                                 |
    | tenant_id  | None                                 |
    | type       | flat                                 |
    | value      | m1.tiny                              |
    +------------+--------------------------------------+


In this example every machine in any project with the flavor m1.tiny will be
charged 0.01 per collection period.


Volume per gb with discount
---------------------------

Now let's do some threshold based rating.

Create a group *volume_thresholds*:

.. code:: raw

    $ cloudkitty hashmap-group-create -n volume_thresholds
    +----------+--------------------------------------+
    | Property | Value                                |
    +----------+--------------------------------------+
    | group_id | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    | name     | volume_thresholds                    |
    +----------+--------------------------------------+

    $ cloudkitty hashmap-group-list
    +-------------------+--------------------------------------+
    | Name              | Group id                             |
    +-------------------+--------------------------------------+
    | volume_thresholds | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    +-------------------+--------------------------------------+


Create the service matching rule:

.. code:: raw

    $ cloudkitty hashmap-service-create -n volume
    +------------+--------------------------------------+
    | Property   | Value                                |
    +------------+--------------------------------------+
    | name       | volume                               |
    | service_id | 16a48060-0e64-11e6-8e4e-1b285514a36e |
    +------------+--------------------------------------+


Now let's setup the price per gigabyte:

.. code:: raw

    $ cloudkitty hashmap-mapping-create \
     -s 16a48060-0e64-11e6-8e4e-1b285514a36e \
     -t flat -c 0.001 -g dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d
    +------------+--------------------------------------+
    | Property   | Value                                |
    +------------+--------------------------------------+
    | cost       | 0.001                                |
    | field_id   | None                                 |
    | group_id   | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    | mapping_id | 41669786-240b-11e6-872c-af96ddb6619c |
    | service_id | 16a48060-0e64-11e6-8e4e-1b285514a36e |
    | tenant_id  | None                                 |
    | type       | flat                                 |
    | value      |                                      |
    +------------+--------------------------------------+


We have the basic price per gigabyte be we now want to apply a discount on huge
data volumes. Create the thresholds in the group *volume_thresholds* that will
map different volume quantity to costs:

Here we set a threshold when going past 50GB, and apply a 2% discount (0.98):

.. code:: raw

    $ cloudkitty hashmap-threshold-create \
     -s 16a48060-0e64-11e6-8e4e-1b285514a36e \
     -l 50 -t rate -c 0.98 -g dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d
    +--------------+--------------------------------------+
    | Property     | Value                                |
    +--------------+--------------------------------------+
    | cost         | 0.98                                 |
    | field_id     | None                                 |
    | group_id     | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    | level        | 50                                   |
    | threshold_id | 8eb45bfc-0e64-11e6-ad0e-07a62425f284 |
    | service_id   | 16a48060-0e64-11e6-8e4e-1b285514a36e |
    | tenant_id    | None                                 |
    | type         | rate                                 |
    +--------------+--------------------------------------+

Here we set the same threshold for project 8f1e8645a0e7496a95a4fdf4b2795b2c
but with a 3% discount (0.97):

.. code:: raw

    $ cloudkitty hashmap-threshold-create \
     -s 16a48060-0e64-11e6-8e4e-1b285514a36e \
     -l 50 -t rate -c 0.98 -g dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d \
     -p 8f1e8645a0e7496a95a4fdf4b2795b2c
    +--------------+--------------------------------------+
    | Property     | Value                                |
    +--------------+--------------------------------------+
    | cost         | 0.97                                 |
    | field_id     | None                                 |
    | group_id     | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    | level        | 50                                   |
    | threshold_id | 8eb45bfc-0e64-11e6-ad0e-07a62425f284 |
    | service_id   | 16a48060-0e64-11e6-8e4e-1b285514a36e |
    | tenant_id    | 8f1e8645a0e7496a95a4fdf4b2795b2c     |
    | type         | rate                                 |
    +--------------+--------------------------------------+

Here we set a threshold when going past 200GB, and apply a 5% discount (0.95):

.. code:: raw

    $ cloudkitty hashmap-threshold-create \
     -s 16a48060-0e64-11e6-8e4e-1b285514a36e \
     -l 200 -t rate -c 0.95 -g dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d
    +--------------+--------------------------------------+
    | Property     | Value                                |
    +--------------+--------------------------------------+
    | cost         | 0.95                                 |
    | field_id     | None                                 |
    | group_id     | dd3dc30e-0e63-11e6-9f83-ab4208c1fe2d |
    | level        | 200                                  |
    | threshold_id | baf180c8-0e64-11e6-abb3-cbae153a6d44 |
    | service_id   | 16a48060-0e64-11e6-8e4e-1b285514a36e |
    | tenant_id    | None                                 |
    | type         | rate                                 |
    +--------------+--------------------------------------+


In this example every volume is charged 0.01 per GB but if the size goes past
50GB you'll get a 2% discount, if you even go further you'll get 5% discount
(only one level apply at a time).

For project 8f1e8645a0e7496a95a4fdf4b2795b2c only, you'll get a 3% discount
instead of 2% when the size goes past 50GB and the same %5 discount it it goes
further.

:20GB: 0.02 per collection period.
:50GB: 0.049 per collection period
    (0.0485 for project 8f1e8645a0e7496a95a4fdf4b2795b2c).
:80GB: 0.0784 per collection period
    (0.0776 for project 8f1e8645a0e7496a95a4fdf4b2795b2c).
:250GB: 0.2375 per collection period.
