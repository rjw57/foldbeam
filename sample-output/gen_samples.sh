#!/bin/sh

THISDIR="${PWD}/`dirname $0`"
WIDTH=852
RENDER="foldbeam-render"
CACHE="${THISDIR}/tilecache"

cd "${THISDIR}"

echo Generate a world map using equirectangular projection
${RENDER} --output world-equirectangular.png -w ${WIDTH} -l -180 -r 180 -t 85 -b -85 --cache-dir "${CACHE}"
echo Generate a world map using mercator projection
${RENDER} --output world-mercator.png -w ${WIDTH} \
    -l -20000000 -t 16000000 -r 20000000 -b -14000000 --epsg 3395 --cache-dir "${CACHE}"
echo Generate the US National Atlas equal area projection
${RENDER} --output us.png -w ${WIDTH} -l -3000000 -t 2500000 -r 3600000 -b -4700000 --epsg 2163 --cache-dir "${CACHE}"
echo Generate a UK OS national grid map with 1 pixel == 1 km
${RENDER} --output uk.png -w 700 -l 0 -r 700000 -t 1300000 -b 0 --epsg 27700 --cache-dir "${CACHE}"
echo Generate a UK OS national grid map centred on Big Ben
${RENDER} --output bigben.png -w ${WIDTH} -l 530069 -t 179830 -r 530469 -b 179430 --epsg 27700 --cache-dir "${CACHE}"
echo Generate a Lambert conformal conic projection
${RENDER} --output lambert-conformal-conic.png -w ${WIDTH} --epsg 2062 \
    -l -8000000 -r 8000000 -t 6000000 -b -4000000 --cache-dir "${CACHE}"

echo Generate a Lambert conformal conic projection
${RENDER} --output lambert-conformal-conic-aerial.png -w ${WIDTH} --epsg 2062 \
    --aerial -l -8000000 -r 8000000 -t 6000000 -b -4000000 --cache-dir "${CACHE}"
echo Generate a UK OS national grid map with 1 pixel == 1 km
${RENDER} --output uk-aerial.png -w 700 \
    --aerial -l 0 -r 700000 -t 1300000 -b 0 --epsg 27700 --cache-dir "${CACHE}"
echo Generate the US National Atlas equal area projection
${RENDER} --output us-aerial.png -w ${WIDTH} \
    --aerial -l -3000000 -t 2500000 -r 3600000 -b -4700000 --epsg 2163 --cache-dir "${CACHE}"

for i in *.png; do convert "$i" "`basename $i .png`.jpg"; rm "$i"; done
