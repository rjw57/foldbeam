"""
Network transparency
====================

Utilising zeromq, foldbeam can launch each node as a separate server process and return a transparent proxy for the
node which can be wired into pipelines. This feature allows a great deal of scalability for foldbeam pipelines while
allowing the logic in each node to consider that it has exclusive access to the interpreter.

"""

import logging
import multiprocessing as mp
import uuid

from notify.all import Signal
import zmq
from zmq.eventloop.ioloop import IOLoop, ZMQPoller
from zmq.eventloop.zmqstream import ZMQStream

log = logging.getLogger(__name__)

EVERYONE    = '\x00' * 16
CREATED     = 'CREATED'
DIE         = 'DIE'

class NodeServerProcess(mp.Process):
    """A process which encapsulates a single node. Each process has a number of zeromq sockets exposed through the
    following attributes:

    .. py:data:: status_socket

        A PUSH socket for sending updates on node status to the manager process. This is used to notify the manager when
        a node is active and ready to be connected.

    .. py:data:: sub_socket

        A SUB socket connected to the manager's PUB socket and filtered by this node's UUID. Used to receive broadcast
        messages such as 'connect this pad' and 'terminate yourself'.

    """

    def __init__(self, status_address, pub_address, node_uuid, module_name, class_name, args, kwargs=None):
        super(NodeServerProcess, self).__init__()
        self.status_address = status_address
        self.pub_address = pub_address
        self.module_name = module_name
        self.class_name = class_name
        self.node_uuid = node_uuid
        self.args = args or []
        self.kwargs = kwargs or {}

    def run(self):
        self.log = logging.getLogger(__name__ + '.node-' + str(self.pid))

        context = zmq.Context()
        self.status_socket = context.socket(zmq.PUSH)
        self.status_socket.connect(self.status_address)

        self.sub_socket = context.socket(zmq.SUB)
        self.sub_socket.subscribe = self.node_uuid.bytes
        self.sub_socket.subscribe = EVERYONE
        self.sub_socket.connect(self.pub_address)

        self.io_loop = IOLoop.instance()
        self.io_loop.add_callback(self._loop_started)

        self.sub_stream = ZMQStream(self.sub_socket, self.io_loop)
        self.sub_stream.on_recv(self._on_sub_recv)

        self.io_loop.start()
        self.log.info('Node server for %s stopped.' % (self.node_uuid,))

    def _loop_started(self):
        module = __import__(self.module_name, fromlist=[self.class_name])
        node_class = getattr(module, self.class_name)
        self.node = node_class(*self.args, **self.kwargs)

        self.log.info('Node server for %s started.' % (self.node_uuid,))
        self._send_multipart_status((CREATED,))

    def _send_multipart_status(self, status_msg):
        msg = [self.node_uuid.bytes,]
        msg.extend(status_msg)
        self.status_socket.send_multipart(msg)

    def _on_sub_recv(self, msg):
        if len(msg) < 1:
            self.log.error('Node %s got empty message.' % (self.node_uuid,))

        if msg[0] != self.node_uuid.bytes and msg[0] != EVERYONE:
            self.log.error('Node %s got malformed message: %s' % (self.node_uuid, msg))

        msg = msg[1:]
        if len(msg) == 1 and msg[0] == DIE:
            self.io_loop.stop()

class Pipeline(object):
    """A central management instance which spawns worker processes for each node in the pipeline.

    """
    def __init__(self, io_loop=None, context=None):
        self.node_created = Signal()
        self.io_loop = io_loop or IOLoop.instance()
        self.context = context or zmq.Context.instance()
        self.node_processes = { }

        address_str = 'tcp://127.0.0.1'

        status_socket = self.context.socket(zmq.PULL)
        port = status_socket.bind_to_random_port(address_str)
        self.status_address = address_str + ':' + str(port)
        log.info('Network status listener bound to ' + self.status_address)

        self.pub_socket = self.context.socket(zmq.PUB)
        port = self.pub_socket.bind_to_random_port(address_str)
        self.pub_address = address_str + ':' + str(port)
        log.info('Network status publisher bound to ' + self.pub_address)

        self.status_stream = ZMQStream(status_socket, io_loop=self.io_loop)
        self.status_stream.on_recv(self._on_recv_status)

    def close(self):
        # Tell everyone to die
        self.pub_socket.send_multipart((EVERYONE, DIE))

        for proc in self.node_processes.itervalues():
            proc.join(1.0)
            if proc.is_alive():
                log.warning('Forcibly terminating node process %i' % (proc.pid,))
                proc.terminate()

        self.node_processes = {}

    def create_node(self, module_name, class_name, args=None, kwargs=None):
        node_uuid = uuid.uuid4()
        node_process = NodeServerProcess(
                self.status_address, self.pub_address,
                node_uuid, module_name, class_name, args, kwargs)
        node_process.daemon = True
        node_process.start()
        self.node_processes[node_uuid] = node_process

    def _on_recv_status(self, msg):
        if len(msg) < 1 or len(msg[0]) != 16:
            log.error('Malformed status message received.')
            return

        node_uuid = uuid.UUID(bytes=msg[0])
        payload = msg[1:]

        if len(payload) == 1 and payload[0] == CREATED:
            self.node_created(node_uuid)
        else:
            log.warning('Unknown message from %s: %s' % (node_uuid, payload))
