from cgi import escape
import colorsys
import json
from foldbeam.pipeline import Pipeline
from foldbeam.core import Envelope
from foldbeam.graph import Node, Pad
from foldbeam.pads import ConstantOutputPad
from osgeo import osr
import os
import sys

sys.path.append(os.path.dirname(__file__))
import sobol_seq

_n_colors = 0
def random_color():
    global _n_colors

    _n_colors += 1
    h = sobol_seq.i4_sobol_generate(1, 1, _n_colors)
    s = 0.9
    l = 0.95
    r, g, b = colorsys.hls_to_rgb(h,l,s)
    return '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))

def pipeline_to_dot(seed_nodes, output_pad, output):
    output.write('''
digraph g {
graph [
    rankdir = "LR"
];
node [
    fontsize = "16"
    shape = "plaintext"
];
''')

    nodes = { }
    pads = { }
    type_colors = { }

    # A function to output a node (or subnode)
    def output_node(node, name, nodes, pads):
        node_name = 'node_%i' % (len(nodes),)
        output.write('subgraph cluster_node_%s {\n' % (node_name,))
        output.write('    style = "filled";\n')
        output.write('    fillcolor = "#f8f8f8";\n')
        output.write('    shape = "rectangle";\n')
        output.write('label = "%s"\n' % (name,))

        output.write('"%s" [\n' % (node_name,))
        output.write('''label = <
<TABLE BGCOLOR="white" CELLSPACING="0" CELLBORDER="1" BORDER="0">
    <TR><TD  BGCOLOR="#eeeeee" PORT="_type"><B>%(type)s</B></TD></TR>
        ''' % dict(name=escape(name), type=escape(node.__class__.__name__)))

        outputs = node.outputs.items()
        inputs = node.inputs.items()

        for pad_name, pad in inputs + outputs:
            if pad.type not in type_colors:
                color = random_color()
                type_colors[pad.type] = color

            output.write('''
    <TR><TD PORT="pad_%(pad_name)s" BGCOLOR="%(type_color)s" ALIGN="%(align)s">%(pad_name)s</TD></TR>
            ''' % dict(
                type_color=type_colors[pad.type],
                pad_name=pad_name,
                align='LEFT' if pad.direction is Pad.IN else 'RIGHT'))
            pads[pad] = ('"%s":%s' % (node_name, 'pad_' + pad_name), node_name)

        output.write('</TABLE>\n>\n')

        output.write(']\n')
        nodes[node] = dict(name=node_name)

        [output_node(x[1], name + '_%i' % x[0], nodes, pads) for x in enumerate(node.subnodes)]
        output.write('}\n')

    # Output all nodes
    [output_node(x[1], x[0], nodes, pads) for x in seed_nodes.iteritems()]

    for node, record in nodes.iteritems():
        for dst_pad in node.inputs.values():
            src_pad = dst_pad.source
            dst_pad_name, dst_node_name = pads[dst_pad]

            if src_pad not in pads and isinstance(src_pad, ConstantOutputPad):
                const_node_name = 'constant_%i' % len(pads)
                output.write('''subgraph cluster_node_%(node_name)s {
                "%(name)s" [
                    label = <<TABLE BGCOLOR="%(color)s" CELLSPACING="0" CELLBORDER="1" BORDER="0">
                    <TR><TD PORT="_value">%(value)s</TD></TR>
                    </TABLE>>
                ]
                }\n''' % dict(
                    color=type_colors[src_pad.type],
                    node_name=record['name'],
                    name=const_node_name,
                    value=escape(str(src_pad.value))))

                pads[src_pad] = ('"%s":_value' % (const_node_name,), record['name'])
            elif src_pad not in pads:
                continue

            src_pad_name, src_node_name = pads[src_pad]
            output.write('%(src)s -> %(dst)s [ ];\n' % dict(src=src_pad_name, dst=dst_pad_name))

    # Add implicit edges to separate out constant nodes
    for node, record in nodes.iteritems():
        for dst_pad in node.inputs.values():
            src_pad = dst_pad.source
            dst_pad_name, dst_node_name = pads[dst_pad]
            src_pad_name, src_node_name = pads[src_pad]

            for dst_pad_name, dst_node_name in [x for x in pads.itervalues() if x[1] == dst_node_name]:
                if src_node_name == dst_node_name:
                    continue
                if dst_pad_name == src_pad_name:
                    continue
                if not dst_pad_name.startswith('"constant'):
                    continue
                output.write('%(src)s -> %(dst)s [ style="invis" ];\n' % dict(src=src_pad_name, dst=dst_pad_name))


    if output_pad in pads:
        output.write('''
            "output" [
                shape = "rectangle"
                label = "Output"
                fillcolor = "%(color)s"
                style = "filled"
            ];
        ''' % dict(color=type_colors[output_pad.type]))
        output.write('%s -> "output" [ ];\n' % (pads[output_pad][0],))

    if len(type_colors) > 0:
        output.write('"legend" [\n')
        output.write('label = <<TABLE CELLSPACING="0" CELLBORDER="1" BORDER="0">\n')
        output.write('<TR><TD BGCOLOR="#eeeeee"><B>Type Key</B></TD></TR>\n')
        for type_, color in type_colors.iteritems():
            if hasattr(type_, 'get_description'):
                label = escape(type_.get_description())
            else:
                label = escape(str(type_))
            output.write('<TR><TD BGCOLOR="%(color)s">%(label)s</TD></TR>\n' % dict(color=color, label=label))
        output.write('</TABLE>>\n')
        output.write(']\n')

    output.write('}\n')

def main():
    config = json.load(open('pipeline.json'))
    pipeline = Pipeline(config)
    pipeline_to_dot(pipeline.nodes, pipeline.output, open('pipeline.dot', 'w'))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(27700) # British National Grid
    envelope = Envelope(360000, 450000, 210000, 100000, srs)

    proj_w, proj_h = map(float, envelope.size())
    proj_aspect = proj_w / proj_h

    w = 852
    size = map(int, (w, w/proj_aspect))
    output = pipeline.output(envelope=envelope, size=size)
    if output is None:
        print('No output generated')
        return
    output.write_tiff('output.tiff')

if __name__ == '__main__':
    main()
