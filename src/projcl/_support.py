import logging
import numpy as np
import os
import pyopencl
import pyopencl.array
import re

def kernel_dir():
    return os.path.join(os.path.dirname(__file__), 'kernels')

def kernel_filename(name):
    filename = os.path.join(kernel_dir(), name + '.cl')
    if not os.path.isfile(filename):
        raise ValueError('Kernel "%s" does not exist.' % name)
    return filename

def kernel_load_program(context, name):
    source = open(kernel_filename(name)).read()
    return kernel_build_program(context, source)

def kernel_build_program(context, source):
    program = pyopencl.Program(context, source)
    try:
        program.build(options = ['-I' + kernel_dir(), '-DUSE_KERNEL'])
    except pyopencl.RuntimeError as e:
        logging.error('Error building program.')
        raise e
    return program

class KernelEntry(object):
    def __init__(self, name=None):
        self.name = name
        self.standard_params = []
        self.custom_params = []
        self.forward_kernel = None
        self.inverse_kernel = None

    def __call__(self, queue, x, y, inverse=False, **kwargs):
        kernel = self.inverse_kernel if inverse else self.forward_kernel
        x = np.array(x, dtype=np.float32).ravel()
        y = np.array(y, dtype=np.float32).ravel()
        input_points = np.array(np.vstack((x,y)), dtype=np.float32, order='F')

        in_array = pyopencl.array.to_device(queue, input_points)
        out_array = pyopencl.array.empty_like(in_array)
        err_array = pyopencl.array.empty(queue, (in_array.shape[1],), dtype=np.int32)

        args = [in_array.data, out_array.data, err_array.data]
        args.extend([kwargs[x] for x in self.standard_params])
        args.extend([kwargs[x] for x in self.custom_params])
        kernel(queue, (in_array.shape[1],), (1,), *args)

        output = out_array.get()
        return output[0,:], output[1,:]

    def __str__(self):
        return '<Projection \'%s\' kernel>' % (self.name,)

def load_projection_kernels(context, name):
    source = open(kernel_filename(name)).read()
    return parse_projection_entries(source, kernel_build_program(context, source))

def parse_projection_entries(kernel_source, program):
    begin_entry = re.compile('BEGIN_ENTRY: (.*)$')
    end_entry = re.compile('END_ENTRY')
    kernels_clause = re.compile('KERNELS:\s*([a-zA-Z_][a-zA-Z0-9_]*),\s*([a-zA-Z_][a-zA-Z0-9_]*)')
    standard_params_clause = re.compile('STANDARD_PARAMS:\s*(.*)$')
    custom_params_clause = re.compile('CUSTOM_PARAMS:\s*(.*)$')

    current_entry = None
    entries = { }

    for l in kernel_source.split('\n'):
        if current_entry is None:
            # look for start of entry
            m = begin_entry.search(l)
            if m:
                current_entry = KernelEntry(m.groups()[0])
                in_entry = True
                continue
        else:
            # look for end of entry
            m = end_entry.search(l)
            if m:
                entries[current_entry.name] = current_entry
                current_entry = None
                continue

            m = kernels_clause.search(l)
            if m:
                forward_kernel, inverse_kernel = m.groups()
                current_entry.forward_kernel = getattr(program, forward_kernel)
                current_entry.inverse_kernel = getattr(program, inverse_kernel)
                continue

            m = standard_params_clause.search(l)
            if m:
                current_entry.standard_params = [x.strip() for x in m.groups()[0].split(',')]
                continue

            m = custom_params_clause.search(l)
            if m:
                current_entry.custom_params = [x.strip() for x in m.groups()[0].split(',')]
                continue

    if current_entry is not None:
        raise RuntimeError('Entry "%s" not ended' % (current_entry.name,))

    return entries
