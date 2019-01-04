======================================
Welcome to CloudKitty's documentation!
======================================

What is CloudKitty ?
====================

CloudKitty is a **Rating-as-a-Service** project for OpenStack and more.
The project aims at being a **generic** solution for the chargeback and rating
of a cloud. Historically, it was only possible to operate it inside of an
OpenStack context, but it is now possible to run CloudKitty in standalone mode.

CloudKitty allows to do metric-based rating: it polls endpoints in order to
retrieve measures and metadata about specific metrics, applies rating rules to
the collected data and pushes the rated data to its storage backend.

CloudKitty is highly modular, which makes it easy to add new features.

.. note::

   **We're looking for contributors!** If you want to contribute, please have
   a look at the `developer documentation`_ .

.. _developer documentation: developer/index.html

What can be done with CloudKitty ? What can't ?
===============================================

**With Cloudkitty, it is possible to:**

- Collect metrics from OpenStack (through Gnocchi and Monasca) or from
  somewhere else (through Gnocchi in standalone mode and Prometheus). Metric
  collection is **highly customizable**.

- Apply rating rules to the previous metrics through the `hashmap`_ module or
  `custom scripts`_. This is all done via CloudKitty's API.

- Retrieve the rated information through the API, grouped by scope and/or by
  metric type.

**However, it is not possible to:**

- Limit resources in other OpenStack services once a certain limit has been
  reached. Ex: block instance creation in Nova above a certain price.
  Cloudkitty does **rating and only rating**.

- Add taxes, convert between currencies, etc... This needs to be done by a
  billing software. CloudKitty associates a price to a metric for a given
  period, but the price's unit is what you decide it to be: euros, dollars,
  cents, squirrels...

.. _hashmap: user/rating/hashmap.html

.. _custom scripts: user/rating/pyscripts.html

Documentation contents
======================

.. list-table::
   :header-rows: 1

   * - Documentation type
     - Table of contents

   * - **End User**
     - .. toctree::
          :maxdepth: 3

          user/index

   * - **Admin / Operator**
     - .. toctree::
          :maxdepth: 2

          admin/index

   * - **Developer**
     - .. toctree::
          :maxdepth: 2

          developer/index

   * - **API Reference**
     - .. toctree::
          :maxdepth: 2

          api-reference/index
