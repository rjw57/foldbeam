from . import _gdal, core, graph
from .graph import InputPad, OutputPad
import numpy as np
from osgeo import osr, gdal

def TiledRasterFilter(render_cb, tile_size=None):
    """

    *render_cb* should take a sequence of (envelope, size) pairs and return a sequence of core.Raster instances (or
    None) for each tile.

    """
    def pull(envelope=None, size=None, **kwargs):
        if envelope is None:
            return None

        if size is None:
            size = map(int, envelope.size())

        if tile_size is None:
            raster = render_cb(envelope=envelope, size=size, **kwargs)
            if raster is None or len(raster) == 0 or raster[0] is None:
                return None
            return raster[0]

        tiles = []
        tile_offsets = []
        xscale, yscale = [x[0] / float(x[1]) for x in zip(envelope.offset(), size)]
        for x in xrange(0, size[0], tile_size):
            width = min(x + tile_size, size[0]) - x
            for y in xrange(0, size[1], tile_size):
                height = min(y + tile_size, size[1]) - y
                tile_envelope = core.Envelope(
                        envelope.left + xscale * x,
                        envelope.left + xscale * (x + width),
                        envelope.top + yscale * y,
                        envelope.top + yscale * (y + height),
                        envelope.spatial_reference,
                )
                tiles.append(render_cb(envelope=tile_envelope, size=(width, height), **kwargs))
                tile_offsets.append((x,y))

        results = [x for x in zip(tile_offsets, tiles) if x[1] is not None]
        if len(results) == 0:
            return None

        # FIXME: This assumes that to_rgba_cb is the same for each tile
        prototype = results[0][1]
        depth = prototype.array.shape[2]

        shape = (size[1], size[0])
        mask = np.ones(shape + (depth,), dtype=np.bool)
        data = np.zeros(shape + (depth,), dtype=np.float32)
        for pos, tile in results:
            x, y = pos
            h, w = tile.array.shape[:2]

            tile_mask = np.ma.getmask(tile.array)
            if tile_mask is np.ma.nomask:
                tile_mask = False

            mask[y:(y+h), x:(x+w), :] = tile_mask
            data[y:(y+h), x:(x+w), :] = tile.array

        if np.any(mask):
            data = np.ma.array(data, mask=mask)

        return core.Raster(data, envelope, prototype=prototype)

    return pull

def ReprojectingRasterFilter(native_spatial_reference, render_cb):
    native_spatial_reference_wkt = native_spatial_reference.ExportToWkt()

    def pull(envelope, size, **kwargs):
        if envelope is None:
            return None

        if size is None:
            size = map(int, envelope.size())

        if envelope.spatial_reference.IsSame(native_spatial_reference):
            return render_cb(envelope, size, **kwargs)

        # We need to reproject this data. Convert the envelope into the native spatial reference
        try:
            native_envelope = envelope.transform_to(
                    native_spatial_reference,
                    min(envelope.size()) / float(max(size)))
        except core.ProjectionError:
            # If we fail to reproject, return a null tile
            return None

        # Get the native tile
        raster = render_cb(envelope=native_envelope, size=size, **kwargs)
        if raster is None:
            return None

        raster_ds = raster.as_dataset()

        # Get the destination raster
        ds = _gdal.create_render_dataset(envelope, size, 4).dataset

        desired_srs_wkt = envelope.spatial_reference.ExportToWkt()
        gdal.ReprojectImage(
                raster_ds, ds,
                native_spatial_reference_wkt,
                desired_srs_wkt,
                gdal.GRA_Bilinear if raster.can_interpolate else gdal.GRA_NearestNeighbour)

        # Create a mask raster
        mask_raster = _gdal.create_render_dataset(envelope, size, 1, data_type=gdal.GDT_Float32)
        mask_ds = mask_raster.dataset
        band = mask_ds.GetRasterBand(1)
        band.SetColorInterpretation(gdal.GCI_Undefined)
        band.SetNoDataValue(float('nan'))
        band.Fill(float('nan'))
        gdal.ReprojectImage(
                raster_ds, mask_ds,
                native_spatial_reference_wkt,
                desired_srs_wkt,
                gdal.GRA_NearestNeighbour)
        mask_band = mask_ds.GetRasterBand(1).GetMaskBand()

        return core.Raster.from_dataset(ds, mask_band=mask_band, prototype=raster)

    return pull
