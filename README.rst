An experiment in dynamic re-projection
======================================

This is my experimental respository for dynamic re-projection work based on the `TileStache`_ project.

Examples
--------

After building with buildout, you should have the `bin/foldbeam-render` script. Some examples:

.. code::
    # Generate a world map using equirectangular projection
    $ bin/foldbeam-render --output world-equirectangular.tiff -w 1280 -l -180 -r 180 -t 89 -b -89
    # Generate a world map using mercator projection
    $ bin/foldbeam-render --output world-mercator.tiff -w 1000 -l -20000000 -t 16000000 -r 20000000 -b -14000000 --epsg 3395
    # Generate the US National Atlas equal area projection
    $ bin/foldbeam-render --output us.tiff -w 1280 -l -3000000 -t 2500000 -r 3600000 -b -4700000 --epsg 2163
    # Generate a UK OS national grid map with 1 pixel == 1 km
    $ bin/foldbeam-render --output uk.tiff -w 700 -l 0 -r 700000 -t 1300000 -b 0 --epsg 27700
    # Generate a UK OS national grid map centred on Big Ben
    $ bin/foldbeam-render --output bigben.tiff -w 800 -l 530069 -t 179830 -r 530469 -b 179430 --epsg 27700

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
