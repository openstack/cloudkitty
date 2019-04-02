=========================
CloudKitty's Architecture
=========================

CloudKitty can be cut in five big parts:

* API
* Data collection (collector)
* Rating processing
* Storage
* Report writer

Module loading and extensions
=============================

Nearly every part of CloudKitty makes use of stevedore to load extensions
dynamically.

Every rating module is loaded at runtime and can be enabled/disabled directly
via CloudKitty's API. The module is responsible of its own API to ease the
management of its configuration.

Collectors and storage backends are loaded with stevedore but configured in
CloudKitty's configuration file.

Collector
=========

**Loaded with stevedore**

The name of the collector to use is specified in the configuration. For now,
only one collector can be loaded at once.
This part is responsible for information gathering. It consists of a python
class that loads data from a backend and returns it in a format that CloudKitty
can handle.

The data format of CloudKitty is the following:

.. code-block:: json

   {
       "myservice": [
           {
               "rating": {
                   "price": 0.1
               },
               "desc": {
                   "sugar": "25",
                   "fiber": "10",
                   "name": "apples",
               },
               "vol": {
                   "qty": 1,
                   "unit": "banana"
               }
           }
       ]
   }


For information about how to write a custom collector, see
the `developer documentation`_.

.. _developer documentation: ../developer/collector.html

Rating
======

**Loaded with stevedore**

This is where every rating calculations is done. The data gathered by the
collector is pushed in a pipeline of rating processors. Every processor does
its calculations and updates the data.

Example of minimal rating module (taken from the Noop module):

.. code-block:: python

    class Noop(rating.RatingProcessorBase):

        controller = NoopController
        description = 'Dummy test module'

        @property
        def enabled(self):
            """Check if the module is enabled

            :returns: bool if module is enabled
            """
            return True

        @property
        def priority(self):
            return 1

        def reload_config(self):
            pass

        def process(self, data):
            for cur_data in data:
                cur_usage = cur_data['usage']
                for service in cur_usage:
                    for entry in cur_usage[service]:
                        if 'rating' not in entry:
                            entry['rating'] = {'price': decimal.Decimal(0)}
            return data

Storage
=======

**Loaded with stevedore**

The storage module is responsible for storing and retrieving data in a
backend. It implements two interfaces (v1 and v2), each providing one or more
drivers. For more information about the storage backend, see the
`configuration section`_.

.. _configuration section: configuration/storage.html

Writer
======

**Loaded with stevedore**

In the same way as the rating pipeline, the writing is handled with a pipeline.
The data is pushed to write orchestrator that will store the data in a
transient DB (in case of output file invalidation). And then to every writer in
the pipeline which is responsible of the writing.
