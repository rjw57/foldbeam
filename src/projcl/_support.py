import os
import pyopencl
import logging

def kernel_dir():
    return os.path.join(os.path.dirname(__file__), 'kernels')

def kernel_filename(name):
    filename = os.path.join(kernel_dir(), name + '.cl')
    if not os.path.isfile(filename):
        raise ValueError('Kernel "%s" does not exist.' % name)
    return filename

def kernel_program(context, name):
    source = open(kernel_filename(name)).read()
    program = pyopencl.Program(context, source)
    try:
        program.build(options = ['-I' + kernel_dir(), '-DUSE_KERNEL'])
    except pyopencl.RuntimeError as e:
        logging.error('Error building program.')
        raise e

    return program
