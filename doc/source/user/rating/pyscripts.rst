=======================
PyScripts rating module
=======================

The PyScripts module allows you to create your own rating module.
A script is supposed to process the given data and to set the
different prices.

CAUTION: If you add several PyScripts, the order in which they will be executed
is not guaranteed.

Custom module example
=====================

Price definitions
-----------------

.. code-block:: python

    import decimal


    # Price for each flavor. These are equivalent to hashmap field mappings.
    flavors = {
        'm1.micro': decimal.Decimal(0.65),
        'm1.nano': decimal.Decimal(0.35),
        'm1.large': decimal.Decimal(2.67)
    }

    # Price per MB / GB for images and volumes. These are equivalent to
    # hashmap service mappings.
    image_mb_price = decimal.Decimal(0.002)
    volume_gb_price = decimal.Decimal(0.35)


Price calculation functions
---------------------------

.. code-block:: python

    # These functions return the price of a service usage on a collect period.
    # The price is always equivalent to the price per unit multiplied by
    # the quantity.
    def get_compute_price(item):
        if not item['desc']['flavor'] in flavors:
            return 0
        else:
            return (decimal.Decimal(item['vol']['qty'])
                   * flavors[item['desc']['flavor']])

    def get_image_price(item):
        if not item['vol']['qty']:
            return 0
        else:
            return decimal.Decimal(item['vol']['qty']) * image_mb_price


    def get_volume_price(item):
        if not item['vol']['qty']:
            return 0
        else:
            return decimal.Decimal(item['vol']['qty']) * volume_gb_price

    # Mapping each service to its price calculation function
    services = {
        'compute': get_compute_price,
        'volume': get_volume_price,
        'image': get_image_price
    }

Processing the data
-------------------

.. code-block:: python

    def process(data):
        # The 'data' is a dictionary with the usage entries for each service
        # in a given period.
        usage_data = data['usage']

        for service_name, service_data in usage_data.items():
            # Do not calculate the price if the service has no
            # price calculation function
            if service_name in services.keys():
                # A service can have several items. For example,
                # each running instance is an item of the compute service
                for item in service_data:
                    item['rating'] = {'price': services[service_name](item)}
        return data


    # 'data' is passed as a global variable. The script is supposed to set the
    # 'rating' element of each item in each service
    data = process(data)


Using your Script for rating
============================

Enabling the PyScripts module
-----------------------------

To use your script for rating, you will need to enable the pyscripts module

.. code-block:: console

    $ cloudkitty module enable pyscripts
    +-----------+---------+----------+
    | Module    | Enabled | Priority |
    +-----------+---------+----------+
    | pyscripts | True    |        1 |
    +-----------+---------+----------+

Adding the script to CloudKitty
-------------------------------

Create the script and specify its name.

.. code-block:: console

    $ cloudkitty pyscript create my_awesome_script script.py
    +-------------------+--------------------------------------+------------------------------------------+---------------------------------------+
    | Name              | Script ID                            | Checksum                                 | Data                                  |
    +-------------------+--------------------------------------+------------------------------------------+---------------------------------------+
    | my_awesome_script | 78e1955a-4e7e-47e3-843c-524d8e6ad4c4 | 49e889018eb86b2035437ebb69093c0b6379f18c | from __future__ import print_function |
    |                   |                                      |                                          | from cloudkitty import rating         |
    |                   |                                      |                                          |                                       |
    |                   |                                      |                                          | import decimal                        |
    |                   |                                      |                                          |                                       |
    |                   |                                      |                                          |         {...}                         |
    |                   |                                      |                                          |                                       |
    |                   |                                      |                                          | data = process(data)                  |
    |                   |                                      |                                          |                                       |
    +-------------------+--------------------------------------+------------------------------------------+---------------------------------------+
