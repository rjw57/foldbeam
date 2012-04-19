class Node(object):
    def __init__(self):
        self.outputs = { }

    def set_input(self, key, value):
        raise KeyError('no such input: ' + key)

    def __setitem__(self, key, value):
        self.set_input(key, value)
