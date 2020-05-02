=========
Collector
=========

Data format
===========

Internally, CloudKitty's data format is a bit more detailled than what can be
found in the `architecture documentation`_.

The internal data format is the following:

.. code-block:: json

   {
       "bananas": [
           {
               "vol": {
                   "unit": "banana",
                   "qty": 1
               },
               "rating": {
                   "price": 1
               },
               "groupby": {
                   "xxx_id": "hello",
                   "yyy_id": "bye",
               },
               "metadata": {
                   "flavor": "chocolate",
                   "eaten_by": "gorilla",
               },
          }
       ],
   }

However, developers implementing a collector don't need to format the data
themselves, as there are helper functions for these matters.

Implementation
==============

Each collector must implement the following class:

.. autoclass:: cloudkitty.collector.BaseCollector
   :noindex:
   :members: fetch_all, check_configuration

The ``retrieve`` method of the ``BaseCollector`` class is called by the
orchestrator. This method calls the ``fetch_all`` method of the child class.

To create a collector, you need to implement at least the ``fetch_all`` method.


Data collection
+++++++++++++++

Collectors must implement a ``fetch_all`` method. This method is called for
each metric type, for each scope, for each collect period. It has the
following prototype:

.. autoclass:: cloudkitty.collector.BaseCollector
   :noindex:
   :members: fetch_all

This method is supposed to return a list of
``cloudkitty.dataframe.DataPoint`` objects.

Example code of a basic collector:

.. code-block:: python

    from cloudkitty.collector import BaseCollector

    class MyCollector(BaseCollector):
        def __init__(self, **kwargs):
            super(MyCollector, self).__init__(**kwargs)

        def fetch_all(self, metric_name, start, end,
                      project_id=None, q_filter=None):
            data = []
            for CONDITION:
                # do stuff
                data.append(dataframe.DataPoint(
                    unit,
                    qty, # int, float, decimal.Decimal or str
                    0, # price
                    groupby, # dict
                    metadata, # dict
                ))

            return data


``project_id`` can be misleading, as it is a legacy name. It contains the
ID of the current scope. The attribute corresponding to the scope is specified
in the configuration, under ``[collect]/scope_key``. Thus, all queries should
filter based on this attribute. Example:

.. code-block:: python

    from oslo_config import cfg

    from cloudkitty.collector import BaseCollector

    CONF = cfg.CONF

    class MyCollector(BaseCollector):
        def __init__(self, **kwargs):
            super(MyCollector, self).__init__(**kwargs)

        def fetch_all(self, metric_name, start, end,
                      project_id=None, q_filter=None):
            scope_key = CONF.collect.scope_key
            filters = {'start': start, 'stop': stop, scope_key: project_id}

            data = self.client.query(
                filters=filters,
                groupby=self.conf[metric_name]['groupby'])
            # Format data etc
            return output


Additional configuration
++++++++++++++++++++++++

If you need to extend the metric configuration (add parameters to the
``extra_args`` section of ``metrics.yml``), you can overload the
``check_configuration`` method of the base collector:

.. autoclass:: cloudkitty.collector.BaseCollector
   :noindex:
   :members: check_configuration

This method uses `voluptuous`_ for data validation. The base schema for each
metric can be found in ``cloudkitty.collector.METRIC_BASE_SCHEMA``. This schema
is meant to be extended by other collectors. Example taken from the gnocchi
collector code:

.. code-block:: python

   from cloudkitty import collector

   GNOCCHI_EXTRA_SCHEMA = {
       Required('extra_args'): {
           Required('resource_type'): All(str, Length(min=1)),
           # Due to Gnocchi model, metric are grouped by resource.
           # This parameter allows to adapt the key of the resource identifier
           Required('resource_key', default='id'): All(str, Length(min=1)),
           Required('aggregation_method', default='max'):
               In(['max', 'mean', 'min']),
       },
   }

   class GnocchiCollector(collector.BaseCollector):

       collector_name = 'gnocchi'

       @staticmethod
       def check_configuration(conf):
           conf = collector.BaseCollector.check_configuration(conf)
           metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
               GNOCCHI_EXTRA_SCHEMA)

           output = {}
           for metric_name, metric in conf.items():
               met = output[metric_name] = metric_schema(metric)

               if met['extra_args']['resource_key'] not in met['groupby']:
                   met['groupby'].append(met['extra_args']['resource_key'])

           return output


If your collector does not need any ``extra_args``, it is not required to
overload the ``check_configuration`` method.


.. _architecture documentation: ../admin/architecture.html

.. _voluptuous: https://github.com/alecthomas/voluptuous
