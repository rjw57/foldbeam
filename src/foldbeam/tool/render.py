import argparse
import TileStache
from foldbeam import nodes, core
from osgeo import gdal
from osgeo.osr import SpatialReference
import sys

def main():
    parser = argparse.ArgumentParser(description='Generate maps of the world from OpenStreetMaps data')
    parser.add_argument('-o', '--output', metavar='FILENAME', type=str, nargs='?',
            required=True, dest='output',
            help='the filename to write the output map in GeoTIFF format')
    parser.add_argument('-p', '--epsg', metavar='EPSG-CODE', type=int, nargs='?',
            dest='epsg', default=4326,
            help='the target projection\'s number in the EPSG database (default: WGS84 latitude/longitude)')
    parser.add_argument('-l', '--left', metavar='NUMBER', type=float, nargs='?',
            required=True, dest='left',
            help='the left-most boundary of the map in projection co-ordinates')
    parser.add_argument('-r', '--right', metavar='NUMBER', type=float, nargs='?',
            required=True, dest='right',
            help='the right-most boundary of the map in projection co-ordinates')
    parser.add_argument('-t', '--top', metavar='NUMBER', type=float, nargs='?',
            required=True, dest='top',
            help='the top boundary of the map in projection co-ordinates')
    parser.add_argument('-b', '--bottom', metavar='NUMBER', type=float, nargs='?',
            required=True, dest='bottom',
            help='the bottom boundary of the map in projection co-ordinates')
    parser.add_argument('-w', '--width', metavar='PIXELS', type=int, nargs='?',
            dest='width', help='the width of the map in pixels (default: use height and projection aspect)')
    parser.add_argument('-e', '--height', metavar='NUMBER', type=int, nargs='?',
            dest='height', help='the height of the map in pixels (default: use width and projection aspect)')
    parser.add_argument('--cache-dir', metavar='DIRECTORY', type=str, nargs='?',
            dest='cache_dir', help='cache downloaded tiles into this directory')
    args = parser.parse_args()

    if args.cache_dir is None:
        cache_config = { 'name': 'Test' }
    else:
        cache_config = { 'name': 'Disk', 'path': args.cache_dir }

    config = TileStache.Config.buildConfiguration({
        'cache': cache_config,
        'layers': {
            'osm': {
                'provider': {
                    'name': 'proxy', 
                    'url': 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{Z}/{X}/{Y}.png',
                },
            },
        },
    })

    envelope = core.Envelope(args.left, args.right, args.top, args.bottom)
    envelope_srs = SpatialReference()
    envelope_srs.ImportFromEPSG(args.epsg)

    if args.width is None and args.height is None:
        print('error: at least one of height or width must be set')
        sys.exit(1)
    elif args.height is None:
        ew, eh = map(abs, envelope.offset())
        args.height = max(1, int(args.width * eh / ew))
    elif args.width is None:
        ew, eh = map(abs, envelope.offset())
        args.width = max(1, int(args.height * ew / eh))
    else:
        assert False

    node = nodes.TileStacheRasterNode(config.layers['osm'])
    size = (args.width, args.height)
    raster = node.render(envelope, envelope_srs, size)

    driver = gdal.GetDriverByName('GTiff')
    driver.CreateCopy(args.output, raster.dataset)

if __name__ == '__main__':
    main()
