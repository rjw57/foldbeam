from cgi import escape
import json
from foldbeam.pipeline import Pipeline
from foldbeam.core import Envelope
from foldbeam.graph import Node
from foldbeam.pads import Pad, ConstantOutputPad
from osgeo import osr

def pipeline_to_dot(nodes, output_pad, output):
    output.write('''
digraph g {
#    ranksep = 1;
#    clusterrank = "none";
graph [
    rankdir = "LR"
];
node [
    fontsize = "16"
    shape = "plaintext"
];
subgraph main {
''')

    to_process = nodes.items()
    subgraphs = {}
    while len(to_process) > 0:
        group, node = to_process[0]
        to_process = to_process[1:]
        if group in subgraphs:
            subgraphs[group].append(node)
        else:
            subgraphs[group] = [node]
        to_process.extend([(group, x) for x in node.subnodes])

    node_records = {}
    connections = []
    pad_containers = {}

    for group_name, nodes in subgraphs.iteritems():
        output.write('subgraph cluster_%s {\n' % (group_name,))
        output.write('    style = "filled";\n')
        output.write('    fillcolor = "#eeffee";\n')
        output.write('    shape = "rectangle";\n')
        output.write('    label = "%s";\n' % (group_name,))
#        output.write('subgraph sourcehack_%s {\nrank="min"\n' % (group_name,))
#        output.write('"source_%s" [\n' % (group_name,))
#        output.write('margin = "0"\nsep = "0"\nlabel = ""\nstyle = "invis"\n')
#        output.write('];\n')
#        output.write('}\n')
#        output.write('subgraph sinkhack_%s {\nrank="max"\n' % (group_name,))
#        output.write('"sink_%s" [\n' % (group_name,))
#        output.write('margin = "0"\nsep = "0"\nlabel = ""\nstyle = "invis"\n')
#        output.write('];\n')
#        output.write('}\n')
        #output.write('"source_%s" -> "sink_%s" [];\n' % (group_name, group_name))
        for idx, node in enumerate(nodes):
            node_name = 'node_%s_%i' % (group_name, idx,)
            node_records[node] = node_name

            output.write('"%s" [\n' % (node_name,))

            inputs = [ ]
            outputs = [ ]

            for pad_name in node.pad_names:
                pad = node.pads[pad_name]
                if pad.direction is Pad.IN:
                    source = pad.source
                    inputs.append((pad_name, source))
                    connections.append((node, pad_name, source, group_name))
                else:
                    outputs.append((pad_name, pad))
                    pad_containers[pad] = (node_name, pad_name, group_name)

            if node.__class__.__module__ != 'foldbeam.nodes':
                title = '%s:%s' % (node.__class__.__module__, node.__class__.__name__)
            else:
                title = node.__class__.__name__

            label = '<TABLE BGCOLOR="white" BORDER="0" CELLBORDER="1" CELLSPACING="0">\n'
            label += '<TR><TD PORT="node" BGCOLOR="#eeeeee"><B>%s</B></TD></TR>\n' % (escape(title),)
            for pad_name, pad in outputs:
                label += '<TR><TD ALIGN="right" PORT="pad_%s">%s</TD></TR>\n' % (pad_name, pad_name)
            for pad_name, pad in inputs:
                label += '<TR><TD ALIGN="left" PORT="pad_%s">%s</TD></TR>\n' % (pad_name, pad_name)
            label += '</TABLE>'

            output.write('    label = <%s>\n' % (label,))
            output.write('];\n')

        output.write('}\n')

    constant_idx = 0
    for dst_node, dst_pad_name, src_pad, dst_group in connections:
        dst_node_name = node_records[dst_node]
        if src_pad in pad_containers:
            src_node_name, src_pad_name, src_group = pad_containers[src_pad]
            src = node_records[subgraphs[src_group][0]]
            dst = node_records[subgraphs[dst_group][-1]]
            if src_group != dst_group:
                output.write('"%s" -> "%s" [style="invis"]\n' % (src, dst))
        elif isinstance(src_pad, ConstantOutputPad):
            constant_idx += 1
            src_node_name = 'constant_%s' % (constant_idx,)
            subgraphs[dst_group].insert(subgraphs[dst_group].index(dst_node) + 1, src_node_name)
            node_records[src_node_name] = src_node_name
            src_pad_name = 'constant'
            output.write('subgraph cluster_%s {\n' % (dst_group,))
            output.write('"%s" [\n' % (src_node_name,))
            output.write('    label = <<TABLE BGCOLOR="#ffeeee" CELLSPACING="0" BORDER="0" CELLBORDER="1">\n')
            output.write('<TR><TD BGCOLOR="#eeeeee"><B>Constant</B></TD></TR>\n')
            output.write('<TR><TD PORT="pad_%s">%s</TD></TR>\n' % (src_pad_name, escape(str(src_pad.value))))
            output.write('</TABLE>>\n')
            output.write('];\n')
            output.write('}\n')
        else:
            continue

        output.write('"%s":pad_%s -> "%s":pad_%s [\n' % (src_node_name, src_pad_name, dst_node_name, dst_pad_name))
        output.write('];\n')

    output.write('}\n')

    if output_pad in pad_containers:
        output.write('''
        subgraph outputsink {
            "output" [
                shape = "rectangle"
                label = "Output"
                fillcolor = "#ccccff"
                style = "filled"
                root = "true"
            ];
        }
        ''')
        node_name, pad_name, _ = pad_containers[output_pad]
        output.write('"%s":pad_%s -> "output" [ ];\n' % (node_name, pad_name))

        #for group in subgraphs.keys():
        #    output.write('"sink_%s" -> "output" [\nstyle="invis"\n];\n' % (group,))

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
