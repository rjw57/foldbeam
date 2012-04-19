import json
from foldbeam.pipeline import Pipeline
from foldbeam.core import Envelope
from foldbeam.pads import ContentType
from osgeo import osr

def config_to_dot(config):
    output = ''
    output += '''
digraph g {
graph [
rankdir = "LR"
];
node [
        fontsize = "16"
        shape = "ellipse"
        ];
edge [
        ];
'''
    
    nodes = {}
    for name, spec in config['nodes'].iteritems():
        assert 'type' in spec
        fields = { }
        if 'parameters' in spec:
            for pname, value in spec['parameters'].iteritems():
                fields[pname] = str(value)
        nodes[name] = { 'name': name, 'type': spec['type'], 'fields': fields }

    edges = []
    for src, dst in config['edges']:
        src_node, src_field = src.split(':')
        dst_node, dst_field = dst.split(':')

        if src_field not in nodes[src_node]['fields']:
            nodes[src_node]['fields'][src_field] = ''
        if dst_field not in nodes[dst_node]['fields']:
            nodes[dst_node]['fields'][dst_field] = ''

        edges.append((src_node, src_field, dst_node, dst_field))

    for name, node in nodes.iteritems():
        fields = ' | '.join(['<f%s> %s %s' % (abs(hash(x[0])), x[0], ('= ' + str(x[1]) if x[1] != '' else '')) for x in node['fields'].iteritems()])
        output += '"%s" [\n' % (name,)
        output += 'label = "node: %s | type: %s | %s"\n' % (name, node['type'], fields)
        output += 'shape = "record"\n'
        output += '];\n'

    for idx, edge in enumerate(edges):
        output += '"%s":f%s -> "%s":f%s [\n' % (edge[0], abs(hash(edge[1])), edge[2], abs(hash(edge[3])))
        output += 'id = %s\n' % (idx,)
        output += '];\n'

    output += '}\n'

    return output

def main():
    config = json.load(open('pipeline.json'))
    open('pipeline.dot', 'w').write(config_to_dot(config))
    pipeline = Pipeline(config)

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
