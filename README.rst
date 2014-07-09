==========
CloudKitty
==========

OpenStack Billing and Usage Reporter
++++++++++++++++++++++++++++++++++++

Goal
----

The goal of this project is to automate the extraction of the metrics from
ceilometer, map them to billing informations and generate reports.

Status
------

This project is **highly** work in progress. Most of the work that we've done was
targeted to quickly create of POC. We are now aiming towards the creation of an
OpenStack module. Changes needed to attain our goal are huge, that's why the
time between commits can be long.

Roadmap
-------

* Create a project API to manage the configuration of billing modules and
  request informations.
* Every billing module should be able to expose its own API.
* Move from importutils to stevedore.
* Scheduling of billing calculations
* Better collection of ceilometer metrics (Maybe Gnocchi)
* Global code improvement


In a possible future :

* Spawning of instances to do the calculations
