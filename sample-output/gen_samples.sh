#!/bin/sh

THISDIR="${PWD}/`dirname $0`"
WIDTH=852
RENDER="${THISDIR}/../bin/foldbeam-render"
CACHE="${THISDIR}/tilecache"

cd "${THISDIR}"

# Generate a world map using equirectangular projection
${RENDER} --output world-equirectangular.tiff -w ${WIDTH} -l -180 -r 180 -t 84 -b -84 --cache-dir "${CACHE}"
# Generate a world map using mercator projection
${RENDER} --output world-mercator.tiff -w ${WIDTH} \
    -l -20000000 -t 16000000 -r 20000000 -b -14000000 --epsg 3395 --cache-dir "${CACHE}"
# Generate the US National Atlas equal area projection
${RENDER} --output us.tiff -w ${WIDTH} -l -3000000 -t 2500000 -r 3600000 -b -4700000 --epsg 2163 --cache-dir "${CACHE}"
# Generate a UK OS national grid map with 1 pixel == 1 km
${RENDER} --output uk.tiff -w 700 -l 0 -r 700000 -t 1300000 -b 0 --epsg 27700 --cache-dir "${CACHE}"
# Generate a UK OS national grid map centred on Big Ben
${RENDER} --output bigben.tiff -w ${WIDTH} -l 530069 -t 179830 -r 530469 -b 179430 --epsg 27700 --cache-dir "${CACHE}"

for i in *.tiff; do convert "$i" "`basename $i tiff`jpg"; done
rm *.tiff
