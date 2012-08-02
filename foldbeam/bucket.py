"""Defines a mechanism for persistent storage of geographic data sets in a way which allows for progressive update of
information such as extent and spatial reference.

"""
import logging
import os
import shutil
import tempfile

import mapnik
from osgeo import ogr, osr, gdal
from shove import Shove

log = logging.getLogger()

class BadFileNameError(Exception):
    """Raised when one attempts to use a bad file name in a bucket. A bad file name is one which contains path
    separators and other 'special' characters in it.
    """
    pass

class Layer(object):
    """An interface for objects returned as layers within a bucket."""

    VECTOR_TYPE = 0
    RASTER_TYPE = 1

    @property
    def type(self):
        """Either :py:attr:`Layer.VECTOR_TYPE` or :py:attr:`Layer.RASTER_TYPE` depending on whether this layer
        is a vector or raster layer."""
        raise NotImplementedError   # pragma: no coverage

    @property
    def name(self):
        """A human-readable name for the layer."""
        raise NotImplementedError   # pragma: no coverage

    @property
    def spatial_reference(self):
        """An instance of :py:class:`osgeo.osr.SpatialReference` giving the spatial reference for this layer or `None`
        if no such spatial reference is available."""
        raise NotImplementedError   # pragma: no coverage

    @property
    def mapnik_datasource(self):
        """A :py:class:`mapnik.Datasource` instance corresponding to this layer or `None` if no such datasource could be
        created."""
        raise NotImplementedError   # pragma: no coverage

class _GDALLayer(object):
    def __init__(self, ds, ds_path):
        self.name = os.path.basename(ds_path)
        self.type = Layer.RASTER_TYPE

        proj_wkt = ds.GetProjection()
        if proj_wkt is not None and proj_wkt != '':
            srs = osr.SpatialReference()
            srs.ImportFromWkt(ds.GetProjection())
            self.spatial_reference = srs
        else:
            self.spatial_reference = None

        self._cached_mapnik_datasource = None
        self._ds_path = ds_path

    @property
    def mapnik_datasource(self):
        if self._cached_mapnik_datasource is not None:
            return self._cached_mapnik_datasource

        self._cached_mapnik_datasource = mapnik.Gdal(file=str(self._ds_path))
        return self._cached_mapnik_datasource

class _OGRLayer(object):
    def __init__(self, layer, ds_path, layer_idx):
        self.name = layer.GetName()
        self.spatial_reference = layer.GetSpatialRef()
        self.type = Layer.VECTOR_TYPE

        self._ds_path = ds_path
        self._layer_idx = layer_idx
        self._cached_mapnik_datasource = None

    @property
    def mapnik_datasource(self):
        if self._cached_mapnik_datasource is not None:
            return self._cached_mapnik_datasource

        self._cached_mapnik_datasource = mapnik.Ogr(
                file=str(self._ds_path),
                layer_by_index=self._layer_idx
        )

        return self._cached_mapnik_datasource

class Bucket(object):
    """A bucket is a single unit of data storage corresponding with, usually, a single data source file. For example
    this might be a single shapefile or a single raster. This single file is called the 'primary file'. There may be
    other files associated with the file. For example, a .SHP file may have an associated .PRJ, .SHX and .DBF file.

    A bucket is similar to a single directory with the restriction that there may be no sub-directories. Files are added
    to the bucket via the :py:meth:`add` method. The first file added becomes the 'primary file'.

    :param storage_dir: a pathname to the directory files within this bucket are stored
    :type storage_dir: str

    """
    def __init__(self, storage_dir):
        self._invalidate_cache()

        self._storage_dir = storage_dir
        assert os.path.exists(self._storage_dir)

        self._shove_url = 'file://' + os.path.join(self._storage_dir, 'metadata')

        self._files_dir = os.path.join(self._storage_dir, 'files')
        if not os.path.exists(self._files_dir):
            os.mkdir(self._files_dir)
        assert os.path.exists(self._files_dir)

    @property
    def files(self):
        """A list of files currently in this bucket."""
        return os.listdir(self._files_dir)

    def add(self, name, fobj):
        """Add a file named `name` to the bucket reading its contents from the file-like object `fobj`.

        :raises BadFileNameError: When `name` is not a raw file name but has, e.g., a directory separator.
        """
        output_file_name = self._file_name_to_path(name)
        log.info('Writing to bucket file: %s' % (output_file_name,))
        try:
            output = open(output_file_name, 'w')
        except IOError: # pragma: no coverage
            # some failure in creating file, we'll assume doe to a bad filename
            raise BadFileNameError('Error creating file named: ' + str(name)) # pragma: no coverage
        shutil.copyfileobj(fobj, output)

        if self.primary_file_name is None:
            self.primary_file_name = name

        self._invalidate_cache()

    @property
    def layers(self):
        """A read only sequence of layers within this bucket. Each element is an object exposing the :py:class:`Layer`
        interface. If the files within the bucket cannot yet be interpreted as a geographic data set then this attribute
        is an empty sequence.
        """
        if self._cached_layers is not None:
            return self._cached_layers

        if self._cached_data_source is None:
            if not self._attempt_to_load():
                return []

        self._cached_layers = self._layer_loader()
        return self._cached_layers

    def _load_ogr_layers(self):
        assert self._cached_data_source is not None
        ds_path = self._file_name_to_path(self.primary_file_name)
        layers = []
        for layer_idx in xrange(self._cached_data_source.GetLayerCount()):
            layer = _OGRLayer(self._cached_data_source.GetLayerByIndex(layer_idx), ds_path, layer_idx)
            layers.append(layer)
        return layers

    def _load_gdal_layers(self):
        assert self._cached_data_source is not None
        ds_path = self._file_name_to_path(self.primary_file_name)

        # A GDAL raster has but one layer
        return [_GDALLayer(self._cached_data_source, ds_path)]

    @property
    def primary_file_name(self):
        """The file name for the 'primary' file in the bucket. It is this file from which data is loaded. Other files
        within the bucket should be auxiliary to this file. (E.g. they should contain projection information.)
        """
        shove = Shove(self._shove_url)
        try:
            return shove['primary_file_name']
        except KeyError:
            return None
        finally:
            shove.close()

    @primary_file_name.setter
    def primary_file_name(self, name):
        assert os.path.exists(self._file_name_to_path(name))
        shove = Shove(self._shove_url)
        try:
            shove['primary_file_name'] = name
        finally:
            shove.close()
        self._invalidate_cache()

    def _invalidate_cache(self):
        self._cached_data_source = None
        self._cached_layers = None
        self._layer_loader = None

    def _file_name_to_path(self, name):
        # check that the file name doesn't try to do anything clever
        if os.path.basename(name) != name or name == '..' or name == '.':
            raise BadFileNameError('%s is an invalid filename' % (name,))
        return os.path.join(self._files_dir, name)

    def _attempt_to_load(self):
        if self.primary_file_name is None:
            return

        self._cached_layers = None
        self._layer_loader = None

        ds_path = self._file_name_to_path(self.primary_file_name)

        # Try with OGR
        self._cached_data_source = ogr.Open(ds_path)
        if self._cached_data_source is not None:
            self._layer_loader = self._load_ogr_layers
            return True

        # Try with GDAL
        self._cached_data_source = gdal.Open(ds_path)
        if self._cached_data_source is not None:
            self._layer_loader = self._load_gdal_layers
            return True
        
        return False
