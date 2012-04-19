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

                self._set_input(dst_name, dst_attr, self._get_output(src_name, src_attr))

        if 'outputs' in configuration:
            for name, output in configuration['outputs'].iteritems():
                node, attr = output.split(':')
                setattr(self, name, self._get_output(node, attr))

    @classmethod
    def _parse_name(cls, name):
        index = None
        if '@' in name:
            name, index = name.split('@')
            index = int(index)
        return index, name

    def _get_output(self, node, name):
        index, name = Pipeline._parse_name(name)
        if index is None:
            return getattr(self.nodes[node], name)
        else:
            return getattr(self.nodes[node], name)[index]

    def _set_input(self, node, name, value):
        index, name = Pipeline._parse_name(name)
        if index is None:
            setattr(self.nodes[node], name, value)
        else:
            getattr(self.nodes[node], name)[index] = value

