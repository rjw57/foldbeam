"""Defines a mechanism for persistent storage of geographic data sets in a way which allows for progressive update of
information such as extent and spatial reference.

"""
import logging
import os
import shutil
import tempfile
import uuid

import cairo
import git
import mapnik
import numpy as np
from PIL import Image
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

    UNKNOWN_SUBTYPE         = 0
    MIXED_SUBTYPE           = 1
    POLYGON_SUBTYPE         = 2
    POINT_SUBTYPE           = 3
    LINESTRING_SUBTYPE      = 4
    MULTIPOLYGON_SUBTYPE    = 5
    MULTIPOINT_SUBTYPE      = 6
    MULTILINESTRING_SUBTYPE = 7

    @property
    def type(self):
        """Either :py:attr:`Layer.VECTOR_TYPE` or :py:attr:`Layer.RASTER_TYPE` depending on whether this layer
        is a vector or raster layer."""
        raise NotImplementedError   # pragma: no coverage

    @property
    def subtype(self):
        """If :py:attr:`type` is :py:attr:`Layer.VECTOR_TYPE`, this is the subtype of the layer or
        :py:attr:`Layer.UNKNOWN_SUBTYPE`.
        """
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

    def render_to_cairo_context(self, ctx, srs, tile_box, tile_size):
        """Return a Cairo ImageSurface representation of this layer for a particular spatial reference, tile extent and tile
        width/height.

        :param ctx: the cairo context to render to
        :param srs: the spatial reference for the tile as a Proj4 projection string
        :param tile_box: the extent of the tile to render in projection co-ordinates
        :type tile_box: tuple of float giving (minx, miny, maxx, maxy)
        :param tile_size: the width and height of the tile to render
        :type tile_size: pair of int giving (width, height)
        :returns: a string containing the encoded PNG.

        """
        raise NotImplementedError   # pragma: no coverage

class _GDALLayer(object):
    def __init__(self, ds, ds_path):
        self.name = os.path.basename(ds_path)
        self.type = Layer.RASTER_TYPE
        self.subtype = Layer.UNKNOWN_SUBTYPE

        proj_wkt = ds.GetProjection()
        if proj_wkt is not None and proj_wkt != '':
            srs = osr.SpatialReference()
            srs.ImportFromWkt(ds.GetProjection())
            self.spatial_reference = srs
        else:
            self.spatial_reference = None

        self._dataset = ds

    def render_to_cairo_context(self, ctx, srs, tile_box, tile_size):
        # get the input dataset
        input_dataset = self._dataset

        input_srs_wkt = input_dataset.GetProjection()
        if input_srs_wkt is None or input_srs_wkt == '':
            return None

        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)

        # create an output dataset
        driver = gdal.GetDriverByName('MEM')
        assert driver is not None
        output_dataset = driver.Create('', tile_size[0], tile_size[1], 4, gdal.GDT_Byte)
        assert output_dataset is not None
        output_dataset.SetGeoTransform((
            tile_box[0], float(tile_box[2]-tile_box[0])/float(tile_size[0]), 0.0,
            tile_box[3], 0.0, -float(tile_box[3]-tile_box[1])/float(tile_size[1])
        ))

        # project input into output
        gdal.ReprojectImage(
                input_dataset, output_dataset,
                input_srs_wkt, spatial_reference.ExportToWkt(),
                gdal.GRA_NearestNeighbour
        )

        # create a cairo image surface for the output. This unfortunately necessitates a copy since the in-memory format
        # for a GDAL Dataset is not interleaved.
        output_array = np.transpose(output_dataset.ReadAsArray(), (1,2,0))

        # swizzle RGBA -> BGRA for Cairo
        output_array = output_array[:,:,(2,1,0,3)]

        output_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tile_size[0], tile_size[1])
        surface_array = np.frombuffer(output_surface.get_data(), dtype=np.uint8)
        surface_array[:] = output_array.flat
        output_surface.mark_dirty()

        ctx.set_source_surface(output_surface)
        ctx.paint()

class _OGRLayer(object):
    def __init__(self, layer, datasource):
        self.name = layer.GetName()
        self.spatial_reference = layer.GetSpatialRef()
        self.type = Layer.VECTOR_TYPE

        wkb_type = layer.GetGeomType()
        if wkb_type == ogr.wkbGeometryCollection:
            self.subtype = Layer.MIXED_SUBTYPE
        elif wkb_type == ogr.wkbPoint:
            self.subtype = Layer.POINT_SUBTYPE
        elif wkb_type == ogr.wkbPolygon:
            self.subtype = Layer.POLYGON_SUBTYPE
        elif wkb_type == ogr.wkbLineString:
            self.subtype = Layer.LINESTRING_SUBTYPE
        elif wkb_type == ogr.wkbMultiPoint:
            self.subtype = Layer.MULTIPOINT_SUBTYPE
        elif wkb_type == ogr.wkbMultiPolygon:
            self.subtype = Layer.MULTIPOLYGON_SUBTYPE
        elif wkb_type == ogr.wkbMultiLineString:
            self.subtype = Layer.MULTILINESTRING_SUBTYPE
        else:
            self.subtype = Layer.UNKNOWN_SUBTYPE

        self._layer = layer
        self._datasource = datasource
        self._cached_mapnik_map = None

    def render_to_cairo_context(self, ctx, srs, tile_box, tile_size):
        datasource = self._datasource

        if self._cached_mapnik_map is None or \
                self._cached_mapnik_map.srs != srs or \
                self._cached_mapnik_map.width != tile_size[0] or \
                self._cached_mapnik_map.height != tile_size[1]:
            mapnik_map = mapnik.Map(tile_size[0], tile_size[1], srs)

            mapnik_map.background = mapnik.Color(0,0,0,0)

            style = mapnik.Style()
            rule = mapnik.Rule()

            subtype = self.subtype
            if self.type is Layer.VECTOR_TYPE:
                if subtype is Layer.POLYGON_SUBTYPE or subtype is Layer.MULTIPOLYGON_SUBTYPE:
                    symb = mapnik.PolygonSymbolizer()
                    symb.fill = mapnik.Color(127,0,0,127)
                    rule.symbols.append(symb)
                elif subtype is Layer.POINT_SUBTYPE or subtype is Layer.MULTIPOINT_SUBTYPE:
                    symb = mapnik.PointSymbolizer()
                    rule.symbols.append(symb)
                elif subtype is Layer.LINESTRING_SUBTYPE or subtype is Layer.MULTILINESTRING_SUBTYPE:
                    symb = mapnik.LineSymbolizer()
                    stroke = mapnik.Stroke()
                    stroke.color = mapnik.Color(0,127,0,127)
                    stroke.width = 2
                    symb.stroke = stroke
                    rule.symbols.append(symb)
                else:
                    return None
            elif self.type is Layer.RASTER_TYPE:
                rule.symbols.append(mapnik.RasterSymbolizer())

            style.rules.append(rule)

            name = uuid.uuid4().hex
            style_name = 'style_%s' % (name,)
            mapnik_map.append_style(style_name, style)

            mapnik_layer = mapnik.Layer(str(name), self.spatial_reference.ExportToProj4())
            mapnik_layer.datasource = datasource
            mapnik_layer.styles.append(style_name)
            mapnik_map.layers.append(mapnik_layer)

            self._cached_mapnik_map = mapnik_map

        mapnik_map = self._cached_mapnik_map
        tile_box = mapnik.Box2d(*tile_box)
        im = mapnik.Image(mapnik_map.width, mapnik_map.height)
        mapnik_map.zoom_to_box(tile_box)
        mapnik.render(mapnik_map, ctx)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tile_size[0], tile_size[1])
        surface.get_data()[:] = im.tostring()
        surface.mark_dirty()
        return surface

class Bucket(object):
    """A bucket is a single unit of data storage corresponding with, usually, a single data source file. For example
    this might be a single shapefile or a single raster. This single file is called the 'primary file'. There may be
    other files associated with the file. For example, a .SHP file may have an associated .PRJ, .SHX and .DBF file.

    A bucket is similar to a single directory with the restriction that there may be no sub-directories. Files are added
    to the bucket via the :py:meth:`add` method. The first file added becomes the 'primary file'.

    :param storage_dir: a pathname to the directory files within this bucket are stored
    :type storage_dir: str

    """

    # A cache keyed on head sha1
    _persistent_layers_cache = {}

    def __init__(self, storage_dir):
        self._storage_dir = storage_dir
        assert os.path.exists(self._storage_dir)

        self._shove_url = 'file://' + os.path.join(self._storage_dir, 'metadata')

        self._files_dir = os.path.join(self._storage_dir, 'files')
        if not os.path.exists(self._files_dir):
            os.mkdir(self._files_dir)
        assert os.path.exists(self._files_dir)

        if not git.repo.fun.is_git_dir(self._files_dir):
            git.Repo.init(self._files_dir)
        self._repo = git.Repo(self._files_dir)

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

        self._repo.index.add([name])
        new_commit = self._repo.index.commit('auto commit')

    @property
    def layers(self):
        """A read only sequence of layers within this bucket. Each element is an object exposing the :py:class:`Layer`
        interface. If the files within the bucket cannot yet be interpreted as a geographic data set then this attribute
        is an empty sequence.
        """
        if len(self._repo.heads) == 0:
            # no data -> no layers
            return []

        # Get the current head and it's hex name
        head = self._repo.heads[0]
        key = head.commit.hexsha

        # Do we have a cached copy of these layers?
        if key in Bucket._persistent_layers_cache:
            return Bucket._persistent_layers_cache[key]

        # Nope, try loading it.
        # Make sure working directory matches head
        head.checkout()

        # Attempt to load the layers and record result in cache
        layers = self._attempt_to_load_layers()
        Bucket._persistent_layers_cache[key] = layers

        return layers

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

    def _file_name_to_path(self, name):
        # check that the file name doesn't try to do anything clever
        if os.path.basename(name) != name or name == '..' or name == '.':
            raise BadFileNameError('%s is an invalid filename' % (name,))
        return os.path.join(self._files_dir, name)

    def _attempt_to_load_layers(self):
        if self.primary_file_name is None:
            return []

        ds_path = self._file_name_to_path(self.primary_file_name)

        # Try with OGR
        ds = ogr.Open(ds_path)
        if ds is not None:
            return self._load_ogr_layers(ds, ds_path)

        # Try with GDAL
        ds = gdal.Open(ds_path)
        if ds is not None:
            return self._load_gdal_layers(ds, ds_path)
        
        # Fail
        return []

    def _load_ogr_layers(self, source, source_path):
        layers = []
        for layer_idx in xrange(source.GetLayerCount()):
            mapnik_datasource = mapnik.Ogr(
                file=str(source_path),
                layer_by_index=layer_idx
            )
            layer = _OGRLayer(source.GetLayerByIndex(layer_idx), mapnik_datasource)
            layers.append(layer)
        return layers

    def _load_gdal_layers(self, source, source_path):
        # A GDAL raster has but one layer
        return [_GDALLayer(source, source_path)]
