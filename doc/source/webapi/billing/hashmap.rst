=======================
HashMap Module REST API
=======================

.. rest-controller:: cloudkitty.billing.hash.controllers.root:HashMapConfigController
   :webprefix: /v1/billing/module_config/hashmap

.. rest-controller:: cloudkitty.billing.hash.controllers.service:HashMapServicesController
   :webprefix: /v1/billing/module_config/hashmap/services

.. autotype:: cloudkitty.billing.hash.datamodels.service.Service
   :members:

.. autotype:: cloudkitty.billing.hash.datamodels.service.ServiceCollection
   :members:

.. rest-controller:: cloudkitty.billing.hash.controllers.field:HashMapFieldsController
   :webprefix: /v1/billing/module_config/hashmap/fields

.. autotype:: cloudkitty.billing.hash.datamodels.field.Field
   :members:

.. autotype:: cloudkitty.billing.hash.datamodels.field.FieldCollection
   :members:

.. rest-controller:: cloudkitty.billing.hash.controllers.mapping:HashMapMappingsController
   :webprefix: /v1/billing/module_config/hashmap/mappings

.. autotype:: cloudkitty.billing.hash.datamodels.mapping.Mapping
   :members:

.. autotype:: cloudkitty.billing.hash.datamodels.mapping.MappingCollection
   :members:

.. rest-controller:: cloudkitty.billing.hash.controllers.group:HashMapGroupsController
   :webprefix: /v1/billing/module_config/hashmap/groups

.. autotype:: cloudkitty.billing.hash.datamodels.group.Group
   :members:

.. autotype:: cloudkitty.billing.hash.datamodels.group.GroupCollection
   :members:
