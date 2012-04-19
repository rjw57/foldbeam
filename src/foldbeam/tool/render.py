import argparse
import TileStache
from foldbeam import nodes, core, graph, pads
from osgeo import gdal
from osgeo.osr import SpatialReference
import sys

parser = argparse.ArgumentParser(description='Generate maps of the world from OpenStreetMaps data')
parser.add_argument('-o', '--output', metavar='FILENAME', type=str, nargs='?',
        required=True, dest='output',
        help='the filename to write the output map in GeoTIFF format')
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
            'aerial': {
                'provider': {
                    'name': 'proxy', 
                    'url': 'http://oatile1.mqcdn.com/naip/{Z}/{X}/{Y}.jpg',
                },
            },
        },
    })

    envelope_srs = SpatialReference()
    if args.epsg is not None:
        envelope_srs.ImportFromEPSG(args.epsg)
    elif args.proj is not None:
        envelope_srs.ImportFromProj4(args.proj)
    else:
        envelope_srs.ImportFromEPSG(4326) # default to WGS84 lat/lng
    envelope = core.Envelope(args.left*args.units, args.right*args.units, args.top*args.units, args.bottom*args.units, envelope_srs)

    if args.width is None and args.height is None:
        print('error: at least one of height or width must be set')
        sys.exit(1)
    elif args.height is None:
        ew, eh = map(abs, envelope.offset())
        args.height = max(1, int(args.width * eh / ew))
    elif args.width is None:
        ew, eh = map(abs, envelope.offset())
        args.width = max(1, int(args.height * ew / eh))

    node = nodes.TileStacheRasterNode(config.layers['aerial' if args.aerial else 'osm'])
    size = (args.width, args.height)
    type_, raster = node.output(envelope, size)
    if type_ != pads.ContentType.RASTER:
        raise RuntimeError('render node did not yield raster')
    raster.write_tiff(args.output)

if __name__ == '__main__':
    main()
