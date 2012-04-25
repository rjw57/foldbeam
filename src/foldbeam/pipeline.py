from __future__ import print_function
from cgi import escape
import json
import traceback
import sys

from foldbeam.graph import connect, Node
import foldbeam.vector
import foldbeam.tilestache

class Pipeline(Node):
    def __init__(self, configuration):
        super(Pipeline, self).__init__()

        self.nodes = { }
        for name, spec in configuration['nodes'].iteritems():
            module_name, class_name = spec['type'].split(':')
            module = __import__(module_name, fromlist=[class_name])
            node_class = getattr(module, class_name)

            kwargs = { }
            if 'parameters' in spec:
                kwargs = spec['parameters']

            try:
                node = node_class(**kwargs)
            except Exception as e:
                print('Error constructing node \'%s\' of type \'%s\':' % (name, spec['type']))
                traceback.print_exc()
                continue

            self.nodes[name] = node

        if 'edges' in configuration:
            for src, dst in configuration['edges']:
                src_name, src_attr = src.split(':')
                dst_name, dst_attr = dst.split(':')

                src = self.nodes[src_name]
                dst = self.nodes[dst_name]

                connect(src.outputs[src_attr], dst.inputs[dst_attr])

        if 'outputs' in configuration:
            for name, output in configuration['outputs'].iteritems():
                node, attr = output.split(':')
                output_pad = self.nodes[node].outputs[attr]
                self.outputs[output_pad.name] = output_pad

def ellipsize(string):
    trunc = string[:40]
    if len(trunc) == len(string):
        return trunc
    return trunc + '...'

def dump_graphviz(file_or_filename, pipeline):
    if isinstance(file_or_filename, basestring):
        output = open(file_or_filename)
    else:
        output = file_or_filename

    output.write('digraph pipeline {\n')
    output.write('''
        rankdir=LR;
        node [ shape=plaintext ];
    ''')

    node_names = {}
    for name, node in pipeline.nodes.iteritems():
        node_names[node] = 'node_' + str(name)
        output.write('"%s" [\n' % (node_names[node],))
        output.write('label = <\n')
        output.write('<TABLE BORDER="0" CELLSPACING="0" CELLBORDER="1">\n')
        output.write('<TR><TD BGCOLOR="#dddddd"><B>%(label)s</B></TD></TR>\n' % {
            'label': escape(node.__class__.__name__)
        })
        for pad_name, pad in node.outputs.iteritems():
            output.write(''''
                <TR><TD PORT="%(name)s" ALIGN="RIGHT">%(label)s</TD></TR>
            ''' % {'name': pad_name, 'label': escape(pad_name)})
        for pad_name, pad in node.inputs.iteritems():
            output.write('''
                <TR><TD PORT="%(name)s" ALIGN="LEFT">%(label)s</TD></TR>
            ''' % {'name': pad_name, 'label': escape(pad_name)})
        output.write('</TABLE>\n')
        output.write('>\n')
        output.write(']\n')

    constant_idx = 0
    for node in pipeline.nodes.itervalues():
        dst_node_name = node_names[node]
        for dst_pad_name, dst_pad in node.inputs.iteritems():
            src_pad = dst_pad.source
            if src_pad is None:
                continue

            src_pad_name = src_pad.name
            src_node = src_pad.container
            if src_node is None:
                continue

            if src_node in node_names:
                src_node_name = node_names[src_node]
            else:
                constant_idx += 1
                src_node_name = 'constant_%i' % (constant_idx,)
                src_pad_name = 'value'
                output.write('''
                "%(name)s" [
                    label=<
                    <TABLE BORDER="0" CELLSPACING="0" CELLBORDER="1">
                    <TR><TD PORT="value">%(value)s</TD></TR>
                    </TABLE>
                    >
                ];
                ''' % {
                    'name': src_node_name, 
                    'pad': src_pad_name,
                    'value': escape(ellipsize(str(src_pad()))),
                }) 

            output.write('''
                "%(src_node_name)s":"%(src_pad_name)s" -> "%(dst_node_name)s":"%(dst_pad_name)s";
            ''' % {
                    'src_node_name': src_node_name, 'src_pad_name': src_pad_name,
                    'dst_node_name': dst_node_name, 'dst_pad_name': dst_pad_name,
                  })

    for output_name, src_pad in pipeline.outputs.iteritems():
        output.write('''
            "output_%(name)s" [
                label = "%(name)s"
                shape = ellipse
            ];
        ''' % {'name': output_name})
        src_node = src_pad.container
        if src_node is None or src_node not in node_names:
            continue
        
        src_node_name = node_names[src_node]
        src_pad_name = src_pad.name

        output.write('"%(src_node_name)s":"%(src_pad_name)s" -> "output_%(name)s";\n' % {
            'src_node_name': src_node_name, 'src_pad_name': src_pad_name,
            'name': output_name,
        })

    output.write('}\n')

def pipeline_to_dot_main():
    p = Pipeline(json.load(sys.stdin))
    dump_graphviz(sys.stdout, p)
