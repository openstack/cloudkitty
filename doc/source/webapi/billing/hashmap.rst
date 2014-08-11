=======================
HashMap Module REST API
=======================

.. rest-controller:: cloudkitty.billing.hash:BasicHashMapController
   :webprefix: /v1/billing/modules/hashmap

.. rest-controller:: cloudkitty.billing.hash:BasicHashMapConfigController
   :webprefix: /v1/billing/modules/hashmap/config

.. http:get:: /v1/billing/hashmap/modules/config/(service)/(field)/(key)

   Get a mapping from full path

   :param service: Filter on this service.
   :param field: Filter on this field.
   :param key: Filter on this key.
   :type service: :class:`unicode`
   :type field: :class:`unicode`
   :type key: :class:`unicode`
   :type mapping: :class:`Mapping`
   :return: A mapping

   :return type: :class:`Mapping`


.. autotype:: cloudkitty.billing.hash.Mapping
   :members:


