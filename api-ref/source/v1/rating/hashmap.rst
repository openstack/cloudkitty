=======================
HashMap Module REST API
=======================

.. rest-controller:: cloudkitty.rating.hash.controllers.root:HashMapConfigController
   :webprefix: /v1/rating/module_config/hashmap

.. rest-controller:: cloudkitty.rating.hash.controllers.service:HashMapServicesController
   :webprefix: /v1/rating/module_config/hashmap/services

.. autoclass:: cloudkitty.rating.hash.datamodels.service.Service
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.service.ServiceCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.field:HashMapFieldsController
   :webprefix: /v1/rating/module_config/hashmap/fields

.. autoclass:: cloudkitty.rating.hash.datamodels.field.Field
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.field.FieldCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.mapping:HashMapMappingsController
   :webprefix: /v1/rating/module_config/hashmap/mappings

.. autoclass:: cloudkitty.rating.hash.datamodels.mapping.Mapping
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.mapping.MappingCollection
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.threshold.Threshold
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.threshold.ThresholdCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.group:HashMapGroupsController
   :webprefix: /v1/rating/module_config/hashmap/groups

.. autoclass:: cloudkitty.rating.hash.datamodels.group.Group
   :members:

.. autoclass:: cloudkitty.rating.hash.datamodels.group.GroupCollection
   :members:
