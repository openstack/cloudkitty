=======================
HashMap Module REST API
=======================

.. rest-controller:: cloudkitty.rating.hash.controllers.root:HashMapConfigController
   :webprefix: /v1/rating/module_config/hashmap

.. rest-controller:: cloudkitty.rating.hash.controllers.service:HashMapServicesController
   :webprefix: /v1/rating/module_config/hashmap/services

.. autotype:: cloudkitty.rating.hash.datamodels.service.Service
   :members:

.. autotype:: cloudkitty.rating.hash.datamodels.service.ServiceCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.field:HashMapFieldsController
   :webprefix: /v1/rating/module_config/hashmap/fields

.. autotype:: cloudkitty.rating.hash.datamodels.field.Field
   :members:

.. autotype:: cloudkitty.rating.hash.datamodels.field.FieldCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.mapping:HashMapMappingsController
   :webprefix: /v1/rating/module_config/hashmap/mappings

.. autotype:: cloudkitty.rating.hash.datamodels.mapping.Mapping
   :members:

.. autotype:: cloudkitty.rating.hash.datamodels.mapping.MappingCollection
   :members:

.. rest-controller:: cloudkitty.rating.hash.controllers.group:HashMapGroupsController
   :webprefix: /v1/rating/module_config/hashmap/groups

.. autotype:: cloudkitty.rating.hash.datamodels.group.Group
   :members:

.. autotype:: cloudkitty.rating.hash.datamodels.group.GroupCollection
   :members:
