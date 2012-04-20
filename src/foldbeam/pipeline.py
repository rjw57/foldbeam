from __future__ import print_function
import traceback

class Pipeline(object):
    def __init__(self, configuration):
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

                dst.pads[dst_attr].connect(src.pads[src_attr])

        if 'outputs' in configuration:
            for name, output in configuration['outputs'].iteritems():
                node, attr = output.split(':')
                setattr(self, name, self.nodes[node].pads[attr])
