An experiment in dynamic re-projection
======================================

This is my experimental respository for dynamic re-projection work based on the `TileStache`_ project.

Examples
--------

After building with buildout, you should have the `bin/foldbeam-render` script. Some examples:

::

    # Generate a world map using equirectangular projection
    $ bin/foldbeam-render --output world-equirectangular.tiff -w 1280 \
        -l -180 -r 180 -t 84 -b -84
    # Generate a world map using mercator projection
    $ bin/foldbeam-render --output world-mercator.tiff -w 1000 \
        -l -20000000 -t 16000000 -r 20000000 -b -14000000 --epsg 3395
    # Generate the US National Atlas equal area projection
    $ bin/foldbeam-render --output us.tiff -w 1280 \
        -l -3000000 -t 2500000 -r 3600000 -b -4700000 --epsg 2163
    # Generate a UK OS national grid map with 1 pixel == 1 km
    $ bin/foldbeam-render --output uk.tiff -w 700 \
        -l 0 -r 700000 -t 1300000 -b 0 --epsg 27700
    # Generate a UK OS national grid map centred on Big Ben
    $ bin/foldbeam-render --output bigben.tiff -w 800 \
        -l 530069 -t 179830 -r 530469 -b 179430 --epsg 27700
    # Generate a Lambert conformal conic projection
    $ bin/foldbeam-render --output lambert-conformal-conic.tiff -w 1024 \
        -l -8000000 -r 8000000 -t 6000000 -b -4000000 --epsg 2062

These examples (and those in the `sample-output/gen_samples.sh` file) generate the output displayed below. Data, imagery
and map information provided by `MapQuest`_, `Open Street Map`_ and contributors, `CC-BY-SA`_.

.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/world-equirectangular.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/world-mercator.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/us.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/us-aerial.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/uk.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/uk-aerial.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/bigben.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/lambert-conformal-conic.jpg
.. figure:: https://github.com/rjw57/foldbeam/raw/master/sample-output/lambert-conformal-conic-aerial.jpg

License
-------

See the `LICENSE-2.0.txt` file.

Credits
-------

- `Distribute`_
- `Buildout`_
- `modern-package-template`_

.. _Buildout: http://www.buildout.org/
.. _Distribute: http://pypi.python.org/pypi/distribute
.. _`modern-package-template`: http://pypi.python.org/pypi/modern-package-template
.. _TileStache: http://tilestache.org/
.. _MapQuest: http://www.mapquest.com/
.. _`Open Street Map`: http://www.openstreetmap.org/
.. _`CC-BY-SA`: http://creativecommons.org/licenses/by-sa/2.0/
