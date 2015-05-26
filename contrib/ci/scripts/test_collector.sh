#!/usr/bin/env bash

show_state()
{
    echo ''
    echo 'Show ceilometer state:'
    echo "GET http://localhost:8888/v1/collector/ceilometer/state"
    curl "http://localhost:8888/v1/collector/ceilometer/state"
    echo ''
    echo "GET http://localhost:8888/v1/collector/state/ceilometer"
    curl "http://localhost:8888/v1/collector/state/ceilometer"
    echo ''
}

set_state()
{
    echo ''
    echo 'Set ceilometer state:'
    echo "PUT http://localhost:8888/v1/collector/ceilometer/state"
    curl "http://localhost:8888/v1/collector/ceilometer/state" \
    -X PUT -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"enabled": true}'
    echo ''
    echo "PUT http://localhost:8888/v1/collector/state/ceilometer"
    curl "http://localhost:8888/v1/collector/state/ceilometer" \
    -X PUT -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"enabled": false}'
    echo ''
}

list_mappings()
{
    echo ''
    echo 'Get compute mapping:'
    echo "GET http://localhost:8888/v1/collector/mappings/compute"
    curl "http://localhost:8888/v1/collector/mappings/compute"
    echo ''

    echo 'List ceilometer mappings:'
    echo "GET http://localhost:8888/v1/collector/ceilometer/mappings"
    curl "http://localhost:8888/v1/collector/ceilometer/mappings"
    echo ''
}

set_mappings()
{
    echo ''
    echo 'Set compute to ceilometer mapping:'
    echo "POST http://localhost:8888/v1/collector/ceilometer/mappings/compute"
    curl "http://localhost:8888/v1/collector/ceilometer/mappings/compute" \
    -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
    -d ''
    echo ''
    echo 'Set volume to ceilometer mapping:'
    echo "POST http://localhost:8888/v1/collector/mappings?collector=ceilometer&service=volume"
    curl "http://localhost:8888/v1/collector/mappings?collector=ceilometer&service=volume" \
    -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
    -d ''
    echo ''
}

del_mappings()
{
    echo ''
    echo 'Deleting compute to ceilometer mapping:'
    echo "DELETE http://localhost:8888/v1/collector/ceilometer/mappings/compute"
    curl "http://localhost:8888/v1/collector/ceilometer/mappings/compute" \
    -X DELETE -H "Content-Type: application/json" -H "Accept: application/json" \
    -d ''
    test $? && echo 'OK'
    echo 'Deleting volume to ceilometer mapping:'
    echo "DELETE http://localhost:8888/v1/collector/mappings?collector=ceilometer&service=volume"
    curl "http://localhost:8888/v1/collector/mappings?collector=ceilometer&service=volume" \
    -X DELETE -H "Content-Type: application/json" -H "Accept: application/json" \
    -d ''
    test $? && echo 'OK'
}

show_state
set_state
list_mappings
set_mappings
list_mappings
del_mappings
list_mappings
