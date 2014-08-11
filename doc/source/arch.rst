=========================
CloudKitty's Architecture
=========================

CloudKitty can be cut in four big parts:

* API
* collector
* billing processor
* writer pipeline


Module loading and extensions
=============================

Nearly every part of CloudKitty makes use of stevedore to load extensions
dynamically.

Every billing module is loaded at runtime and can be enabled/disabled directly
via CloudKitty's API. The billing module is responsible of its own API to ease
the management of its configuration.

Collectors and writers are loaded with stevedore but configured in CloudKitty's
configuration file.


Collector
=========

This part is responsible of the information gathering. It consists of a python
module that load data from a backend and return them in a format that
CloudKitty can handle.

Processor
=========

This is where every pricing calculations is done. The data gathered by
the collector is pushed in a pipeline of billing processors. Every
processor does its calculations and updates the data.


Writer
======

In the same way as the processor pipeline, the writing is handled with a
pipeline. The data is pushed to every writer in the pipeline which is
responsible of the writing.
