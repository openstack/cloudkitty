.. raw:: html

    <style> .roadmap-not-started {background: #EF9A9A} </style>
    <style> .roadmap-started {background: #FFF59D} </style>
    <style> .roadmap-review {background: #90CAF9} </style>
    <style> .roadmap-done {background: #A5D6A7} </style>
    <style> .roadmap-good-first-contribution {background: #80DEEA} </style>

.. role:: roadmap-not-started
.. role:: roadmap-started
.. role:: roadmap-review
.. role:: roadmap-done
.. role:: roadmap-good-first-contribution

=========
 Roadmap
=========

This is the roadmap for planned changes in CloudKitty. Changes are split into:

* Continuous

* Short-term (planned for the next release)

* Mid-term (ideally for the next release, else for release R+2)

* Long-term (for changes that will definitely not happen
  during the next release).

.. note:: This document must be kept up-to-date.  Any newly planned feature
          should be added. The statuses of the existing features should be
          updated regularly. At each release, it is the CloudKitty's PTL's
          responsibility to remove the changes that have been merged during
          the previous release.

How to edit this document
=========================

The first two columns should not need to be modified. If there are several
assignees to a change, you can either specify each person individually or
write the word ``multiple`` in the ``Assignees`` column.

Status columns can be in four states:

* :roadmap-not-started:`Not started`
* :roadmap-started:`Started`
* :roadmap-review:`Review`
* :roadmap-done:`Done`

See the source file of this document for highlighting syntax
(``doc/source/developer/roadmap.rst``).

Continuous effort
=================

Some points deserve continuous effort. These are not tied to a specific
release, but are some of the most important aspects of the project. Some of
these can be good first contributions.

* **Welcoming and mentoring new contributors.** Reviewers should be especially
  kind when reviewing a person's first contribution. Don't assume that they
  know the "developer workflow" document and OpenStack guidelines by heart,
  and point them to the right resources if needed.

* **Improving the documentation.** This includes migrating documentation to
  the new format (adopt a user-profile and component-based layout), but also
  adding information you figured out by yourself and couldn't find in the
  existing documentation (for example: notes for specific configuration
  options, some examples, additional explanations on some notions that may be
  difficult to grasp for newcomers...).

* **Improving the troubleshooting documentation.** The creation of this
  documentation is part of the mid-term effort (see below). It will be
  especially useful for new users.
  :roadmap-good-first-contribution:`Good first contribution`

* **Adding tests.** There are *never* enough tests, so don't be shy and feel
  free to improve the current unit tests or add some scenarios to the tempest
  plugin.
  :roadmap-good-first-contribution:`Good first contribution`

Short-term effort
=================

.. list-table::
   :header-rows: 1

   * - Planned Change
     - Assignees
     - Spec status
     - Implementation status
     - Short summary

   * - Adding the v2 API
     - peschk_l
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - The new API of CloudKitty, to which all new endpoints will be added.

   * - Support local timezones
     - peschk_l
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - Currently, CloudKitty converts all dates to UTC and is not
       timezone-aware. This must be changed in order to get a better user
       experience.

   * - Add a Prometheus scope fetcher
     - jferrieu
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - A scope fetcher that will work in a similar way to the Gnocchi fetcher
       (retrieving all values for a given metadata field on a set of metrics).

   * - Add support for the v2 API to the client
     - peschk_l
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - Add the necessary base to the client to start supporting v2 API
       endpoints.

   * - Add a v2 API endpoint allowing to reset the state of a scope
     - jferrieu
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - This will allow to delete all the data for a specific scope after a
       given date, and reset the state of this scope to that date.

   * - Add a V2 API endpoint allowing to retrieve rating information
     - Multiple
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - This will be an improved version of the ``/summary`` endpoint available
       in the v1 API. It will allow grouping of data on any groupby attribute.

   * - Add a v2 API endpoint allowing to generate reports
     - jferrieu
     - :roadmap-started:`Started`
     - :roadmap-not-started:`Not started`
     - This will be a replacement for ``cloudkitty-writer``.

Mid-term effort
===============

.. list-table::
   :header-rows: 1

   * - Planned Change
     - Assignees
     - Spec status
     - Implementation status
     - Short summary

   * - Creating a new rating module
     - Multiple
     - :roadmap-started:`Started`
     - :roadmap-not-started:`Not started`
     - This module will add support for validity periods on rating rules,
       rulesets and will allow rule creation in a declarative way.

   * - Add a second v2 storage backend
     - peschk_l
     - :roadmap-review:`Review:` https://review.opendev.org/#/c/673461/
     - :roadmap-not-started:`Not started`
     - An alternative to InfluxDB, with support for clustering. For now,
       Elasticsearch has been retained.

   * - Add a troubleshooting documentation
     - Multiple
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - A documentation providing responses, checklists and tutorials to the
       most frequently asked questions on the ``#cloudkitty`` IRC channel.


Long-term effort
================

.. list-table::
   :header-rows: 1

   * - Planned Change
     - Assignees
     - Spec status
     - Implementation status
     - Short summary

   * - Complete migration of the v1 API into v2
     - Multiple
     - :roadmap-started:`Started`
     - :roadmap-not-started:`Not started`
     - Making every (if not deprecated) endpoint of the v1 API available in
       the v2 API.

   * - Adding authentication middlewares to the API in case it is used without
       keystone.
     - Undefined
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - This would allow support for RBAC outside of an openstack context.

API Migration status
====================

.. note:: v1 API endpoints which are not listed below will not be migrated.

.. list-table::
   :header-rows: 1

   * - v1 endpoint
     - Spec
     - Endpoint
     - Client
     - Tempest tests

   * - ``GET /v1/info/config``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/info/metric``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/modules``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``PUT /v1/rating/modules``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/quote``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/report/summary``
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/storage/dataframes``
     - :roadmap-done:`Done`
     - :roadmap-done:`Done`
     - :roadmap-review:`Review: https://review.opendev.org/#/c/681660/`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/pyscripts/scripts``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/module_config/pyscripts/scripts``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``PUT /v1/rating/module_config/pyscripts/scripts``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``DELETE /v1/rating/module_config/pyscripts/scripts``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/types``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/services``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/module_config/hashmap/services``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``DELETE /v1/rating/module_config/hashmap/services``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/fields``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/module_config/hashmap/fields``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``DELETE /v1/rating/module_config/hashmap/fields``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/mappings``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/module_config/hashmap/mappings``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``PUT /v1/rating/module_config/hashmap/mappings``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``DELETE /v1/rating/module_config/hashmap/mappings``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/mappings/group``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/groups``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``POST /v1/rating/module_config/hashmap/groups``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``DELETE /v1/rating/module_config/hashmap/groups``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/groups/mappings``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`

   * - ``GET /v1/rating/module_config/hashmap/groups/thresholds``
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
     - :roadmap-not-started:`Not started`
