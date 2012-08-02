#!/bin/sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd ${DIR}

function put() {
    echo "Putting to $1" >&2
    URL=`http -p h PUT $* | grep '^Location:' | sed -e 's/^Location:\s*//'`
    if [ -z "${URL}" ]; then
        echo "Error loading $1" >&2
        exit 1
    fi
    echo -n ${URL//[[:space:]]/}
}

function post() {
    echo "Posting to $1" >&2
    URL=`http -p h POST $* | grep '^Location:' | sed -e 's/^Location:\s*//'`
    if [ -z "${URL}" ]; then
        echo "Error loading $1" >&2
        exit 1
    fi
    echo -n ${URL//[[:space:]]/}
}

function put_file() {
    echo "Posting $2 to $1" >&2
    URL=`http -p h PUT $1 contents@$2 | grep '^Location:' | sed -e 's/^Location:\s*//'`
    if [ -z "${URL}" ]; then
        echo "Error loading $1" >&2
        exit 1
    fi
    echo -n ${URL//[[:space:]]/}
}

function get_uuid() {
    http -p b GET $* | sed -e 's/.*"uuid": "\([a-f0-9]*\)".*/\1/'
}

put http://localhost:8888/user1 >/dev/null
put http://localhost:8888/user2 >/dev/null
put http://localhost:8888/user3 >/dev/null

B1=`post http://localhost:8888/user1/bucket name="shapefile_test"`
put_file ${B1}/foo.shp ../data/ne_110m_admin_0_countries.shp
put_file ${B1}/foo.shx ../data/ne_110m_admin_0_countries.shx
put_file ${B1}/foo.dbf ../data/ne_110m_admin_0_countries.dbf
put_file ${B1}/foo.prj ../data/ne_110m_admin_0_countries.prj

B2=`post http://localhost:8888/user1/bucket name="tiff_test"`
put_file ${B2}/input.tiff ../data/spain.tiff

B3=`post http://localhost:8888/user1/bucket name="png_test_1"`
put_file ${B3}/input.png ../data/spain.png

B4=`post http://localhost:8888/user1/bucket name="png_test_2"`
put_file ${B4}/input.png ../data/spain.png
put_file ${B4}/input.png.aux.xml ../data/spain.png.aux.xml

M1=`post http://localhost:8888/user1/map`
M1L1=`post ${M1}/layer`
M1L2=`post ${M1}/layer name=Postcodes`

B1ID=`get_uuid ${B1}`
B2ID=`get_uuid ${B2}`

post ${M1L1} "name:=\"spain_and_countries\"" >/dev/null
post ${M1L1} "bucket:=\"${B1ID}\"" >/dev/null

#M2=`post http://localhost:8888/user1/map`
#M2L1=`post ${M2}/layer`
#M2L2=`post ${M2}/layer`

