#!/bin/sh

function put() {
    echo "Putting to $@" >&2
    URL=`http -p h PUT $@ | grep '^Location:' | sed -e 's/^Location:\s*//'`
    if [ -z "${URL}" ]; then
        echo "Error loading $@" >&2
        exit 1
    fi
    echo -n ${URL//[[:space:]]/}
}

function post() {
    echo "Posting to $@" >&2
    URL=`http -p h POST $@ | grep '^Location:' | sed -e 's/^Location:\s*//'`
    if [ -z "${URL}" ]; then
        echo "Error loading $@" >&2
        exit 1
    fi
    echo -n ${URL//[[:space:]]/}
}

put http://localhost:8888/user1
put http://localhost:8888/user2
put http://localhost:8888/user3

M1=`post http://localhost:8888/user1/map`
M1L1=`post ${M1}/layer`
M1L2=`post ${M1}/layer`

M2=`post http://localhost:8888/user1/map`
M2L1=`post ${M2}/layer`
M2L2=`post ${M2}/layer`

