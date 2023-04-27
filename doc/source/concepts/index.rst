CloudKitty Concepts
======================

This page provides the definitions for the concepts used in CloudKitty.
It is recommended that you get familiar with them.


Rating
------
It is the process of assigning a `value` to the consumption of computing
resources. CloudKitty uses the concepts of services, which are rated.
Therefore, one can configure services to be collected/monitored, and
then through its processes, we can assign monetary values to the
service consumption.

The `value` assigned can be used to represent a monetary value in any
currency. However, CloudKitty has no native module to execute conversions
and apply any currency rate. The process to map/link a `value` to a real
monetary charge is up to operators when configuring CloudKitty.

Modules
-------

Modules define the rating processes that are enabled. To get to know more about
the rating modules, one should check `rating modules`_ .

.. _rating modules: ../user/rating/index.html


Services
--------

Services define the metrics that are collected in a storage backend, and that
are then rated by CloudKitty. Services need to be defined via API to be
processed later by the rating modules, and configured in the collectors to be
captured. Services are configured to be collected in the ``metrics.yml`` file.
More information about service creation can be found at the `service
configuration page`_.

.. _service configuration page: ../admin/configuration/configuration.html


Groups
------

Groups define sets of services that can be manipulated together. Groups are
directly linked to rating rules, and not to services or fields.
Therefore, if we want to group a set of rules to list them together
or delete them, we can create a group and add them to the group, but
in the end the resources are going to be charged based on the
services, fields and rating rules.

Fields
------

Fields define the attributes that are retrieved together with the service
collection that can be used to activate a rating rule.


PyScripts
---------
It is an alternative method of writing rating rule. When writing a PyScript,
one will be able to handle the complete processing of the rating.
Therefore, there is no need to create services, fields, and groups
in CloudKitty. The PyScript logic should take care of all that.

Rating rules
------------
Rating rules are the expressions used to create a charge (assign a value to
a computing resource consumption). Rating rules can be created with
PyScripts or with the use of fields, services and groups with hashmap
rating rules.

If we have a hashmap mapping configuration for a service and another
hashmap map configuration for a field that belongs to the same service,
the user is going to be charged twice, one for service and another for
the field that activated a rating rule that is linked to the service.

Rating type
-----------
Rating type is the expression used to determine a service definition in the
collection backend. For instance, one can use the following syntax
in the ``metrics.yml`` file. The entry
``dynamic_pollster.compute.services.instance.status`` is the definition
for rating types. In the example shown here, there are two rating
types being defined, one called ``instance-usage-hours`` and the other
called ``instance-operating-system-license``. The rating types are
configured in CloudKitty API as services. If they are not configured,
they will not be rated by rating rules defined with hashmap. Therefore,
they would be collected, and persisted with value (price) as zero.

..  code-block:: yaml

    metrics:
      dynamic_pollster.compute.services.instance.status:
        - unit: instance
          alt_name: instance-usage-hours
          description: "compute"
          groupby:
            - id
            - display_name
            - flavor_id
            - flavor_name
            - user_id
            - project_id
            - revision_start
            - availability_zone
          metadata:
            - image_ref
            - flavor_vcpus
            - flavor_ram
            - operating_system_name
            - operating_system_distro
            - operating_system_type
            - operating_system_version
            - mssql_version
          extra_args:
            aggregation_method: max
            resource_type: instance
            use_all_resource_revisions: false
        - unit: license-hours
          alt_name: "instance-operating-system-license"
          description: "license"
          groupby:
            - id
            - display_name
            - flavor_id
            - flavor_name
            - user_id
            - project_id
            - revision_start
            - availability_zone
            - operating_system_distro
            - operating_system_name
          metadata:
            - image_ref
            - flavor_vcpus
            - flavor_ram
            - operating_system_type
            - operating_system_version
          extra_args:
            aggregation_method: max
            resource_type: instance
            use_all_resource_revisions: false

