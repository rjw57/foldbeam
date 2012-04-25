from cgi import escape
import colorsys
import json
from foldbeam.pipeline import Pipeline
from foldbeam.core import Envelope
from foldbeam.graph import Node, Pad
from osgeo import osr
import os
import sys

sys.path.append(os.path.dirname(__file__))
from test_pipeline import pipeline_to_dot

def main():
    config = dict(
        nodes = dict(
            tilestache = dict(
                type = 'foldbeam.raster:TileStacheSource',
                parameters = dict(config_file = os.path.join(os.path.dirname(__file__), 'base-layers-cfg.json')),
            ),
            hybrid = dict(
                type = 'foldbeam.raster:CompositeOver',
                parameters = dict(top_opacity = 0.5),
            ),
            composite = dict(
                type = 'foldbeam.raster:CompositeOver',
            ),
            vector = dict(
                type = 'foldbeam.vector:VectorRendererNode',
                parameters = dict(
                    filename = 'stops.db',
                    sql = 'SELECT * FROM Stops WHERE BusStopType = "MKD"',
                    pen_rgba = (0.3, 0.0, 0.3, 0.3),
                )
            ),
        ),
        edges = [
            [ 'tilestache:yahoo_road', 'hybrid:top' ],
            [ 'tilestache:yahoo_aerial', 'hybrid:bottom' ],
            [ 'hybrid:output', 'composite:bottom' ],
            [ 'vector:output', 'composite:top' ],
        ],
        outputs = dict(
            output = 'composite:output',
        ),
    )
    json.dump(config, open('vector_pipeline.json', 'w'), indent=4)
    pipeline = Pipeline(config)
    pipeline_to_dot(pipeline.nodes, pipeline.outputs.values()[0], open('pipeline.dot', 'w'))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(27700) # British National Grid
    envelope = Envelope(500000, 600000, 300000, 200000, srs)

    proj_w, proj_h = map(float, envelope.size())
    proj_aspect = proj_w / proj_h

    w = 512
    size = map(int, (w, w/proj_aspect))
    output = pipeline.outputs.values()[0](envelope=envelope, size=size)
    if output is None:
        print('No output generated')
        return
    output.write_tiff('output.tiff')

if __name__ == '__main__':
    main()
