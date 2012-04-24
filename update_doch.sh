#!/bin/sh
THISDIR=`dirname $0`
cd ${THISDIR}

DOCFILES=`pushd "docs/html/" >/dev/null; find .; popd >/dev/null`
cp -r docs/html/* .
for f in ${DOCFILES}; do
    git add "${f}"
done
git commit -m "Automated commit on `date`"

