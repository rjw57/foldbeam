import json
from foldbeam.pipeline import Pipeline
from foldbeam.core import Envelope
from foldbeam.pads import ContentType
from osgeo import osr

def main():
    pipeline = Pipeline(json.load(open('pipeline.json')))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(27700) # British National Grid
    envelope = Envelope(360000, 450000, 210000, 100000, srs)

    proj_w, proj_h = map(float, envelope.size())
    proj_aspect = proj_w / proj_h

    w = 852
    size = map(int, (w, w/proj_aspect))
    output = pipeline.output(envelope, size)

    assert output is not None
    type_, raster = output

    assert type_ is ContentType.RASTER
    raster.write_tiff('output.tiff')

if __name__ == '__main__':
    main()
