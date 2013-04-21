import argparse
import logging
import sys

import cairo
import httplib2
from osgeo import gdal
from osgeo.osr import SpatialReference

from foldbeam.rendering.renderer import TileFetcher, set_geo_transform

logging.basicConfig(level=logging.WARNING)

parser = argparse.ArgumentParser(description='Generate maps of the world from OpenStreetMaps data')
parser.add_argument('-o', '--output', metavar='FILENAME', type=str, nargs='?',
        required=True, dest='output',
        help='the filename to write the output map in PNG format')
parser.add_argument('-p', '--epsg', metavar='EPSG-CODE', type=int, nargs='?',
        dest='epsg', help='the target projection\'s number in the EPSG database')
parser.add_argument('--proj', metavar='PROJ-INITIALISER', type=str, nargs='?',
        help='the target projection\'s proj4-style initialiser')
parser.add_argument('-l', '--left', metavar='NUMBER', type=float, nargs='?',
        required=True, dest='left',
        help='the left-most envelope of the map in projection co-ordinates')
parser.add_argument('-r', '--right', metavar='NUMBER', type=float, nargs='?',
        required=True, dest='right',
        help='the right-most envelope of the map in projection co-ordinates')
parser.add_argument('-t', '--top', metavar='NUMBER', type=float, nargs='?',
        required=True, dest='top',
        help='the top envelope of the map in projection co-ordinates')
parser.add_argument('-b', '--bottom', metavar='NUMBER', type=float, nargs='?',
        required=True, dest='bottom',
        help='the bottom envelope of the map in projection co-ordinates')
parser.add_argument('-u', '--units', metavar='NUMBER', type=float, nargs='?',
        default=1.0, help='scale left, right, top and bottom by NUMBER (default: 1)')
parser.add_argument('-w', '--width', metavar='PIXELS', type=int, nargs='?',
        dest='width', help='the width of the map in pixels (default: use height and projection aspect)')
parser.add_argument('-e', '--height', metavar='NUMBER', type=int, nargs='?',
        dest='height', help='the height of the map in pixels (default: use width and projection aspect)')
parser.add_argument('--cache-dir', metavar='DIRECTORY', type=str, nargs='?',
        dest='cache_dir', help='cache downloaded tiles into this directory')
parser.add_argument('--aerial', action='store_true', default=False, help='use aerial imagery')
    
def main(argv=None):
    run(parser.parse_args(argv))

def run(args):
    srs = SpatialReference()
    if args.epsg is not None:
        srs.ImportFromEPSG(args.epsg)
    elif args.proj is not None:
        srs.ImportFromProj4(args.proj)
    else:
        srs.ImportFromEPSG(4326) # default to WGS84 lat/lng

    left, right, top, bottom = (
        args.left*args.units,
        args.right*args.units,
        args.top*args.units,
        args.bottom*args.units
    )

    if args.width is None and args.height is None:
        print('error: at least one of height or width must be set')
        sys.exit(1)
    elif args.height is None:
        ew, eh = (abs(right-left), abs(top-bottom))
        args.height = max(1, int(args.width * eh / ew))
    elif args.width is None:
        ew, eh = (abs(right-left), abs(top-bottom))
        args.width = max(1, int(args.height * ew / eh))

    size = (args.width, args.height)

    url_patterns = {
        'osm': 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{zoom}/{x}/{y}.jpg',
        'aerial': 'http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
    }

    def url_fetcher(url):
        http = httplib2.Http(args.cache_dir)
        rep, content = http.request(url, 'GET')
        if rep.status != 200:
            raise foldbeam.renderer.URLFetchError(str(rep.status) + ' ' + rep.reason)
        return content

    renderer = TileFetcher(
            url_pattern=url_patterns['aerial' if args.aerial else 'osm'],
            url_fetcher=url_fetcher)


    if args.output.endswith('.tiff'):
        from osgeo import gdal_array, gdal
        import numpy as np
        image_data = np.zeros((size[1], size[0], 4), dtype=np.uint8)
        output_surface = cairo.ImageSurface.create_for_data(
                image_data, cairo.FORMAT_ARGB32, size[0], size[1])
        context = cairo.Context(output_surface)
        set_geo_transform(context, left, right, top, bottom, size[0], size[1])
        renderer.render_callable(context, spatial_reference=srs)()
        ds = gdal_array.OpenArray(
                np.transpose(image_data[:,:,[2,1,0,3]], (2,0,1)))

        ds.SetGeoTransform((
            left, (right - left) / size[0], 0,
            top, 0, (bottom - top) / size[1]
        ))

        drv = gdal.GetDriverByName('GTiff')
        drv.Delete(args.output)
        drv.CreateCopy(args.output, ds)
    else:
        output_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])
        context = cairo.Context(output_surface)
        set_geo_transform(context, left, right, top, bottom, size[0], size[1])
        renderer.render_callable(context, spatial_reference=srs)()
        output_surface.write_to_png(args.output)

if __name__ == '__main__':
    main()
