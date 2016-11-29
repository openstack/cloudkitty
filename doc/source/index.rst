.. cloudkitty documentation master file, created by
   sphinx-quickstart on Wed May 14 23:05:42 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================================================
Welcome to CloudKitty's developer documentation!
=================================================

Introduction
============

CloudKitty is a Rating As A Service project aimed at translating metrics
to prices.

Installation
============

.. toctree::
   :maxdepth: 1

   devstack
   installation


Architecture
============

.. toctree::
   :maxdepth: 1

   arch


API References
==============

.. toctree::
   :maxdepth: 1

   webapi/root
   webapi/v1


Modules API
===========

.. toctree::
   :maxdepth: 1
   :glob:

   webapi/rating/*

Rating Module Documentation
===========================

.. toctree::
   :maxdepth: 1

   rating/introduction.rst
   rating/hashmap.rst
   rating/pyscripts.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
