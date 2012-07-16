#!/bin/sh
THISDIR=`dirname $0`
cd ${THISDIR}

DOCFILES=`pushd "build/sphinx/html/" >/dev/null; find . -type f; popd >/dev/null`
cp -rv build/sphinx/html/* build/sphinx/html/.* .
for f in ${DOCFILES}; do
    echo "Adding ${f}"
    git add "${f}"
done
git commit -m "Automated commit on `date`"

