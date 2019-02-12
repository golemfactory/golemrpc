import asyncio
import functools
import logging
import os
import queue
import signal
import sys
import threading
import traceback
import txaio

from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

from .utils import create_component
from .handlers.singlerpc import SingleRPCCallHandler
from .handlers.task import TaskMessageHandler, TaskRemoteFSDecorator,\
    TaskRemoteFSMappingDecorator
from .handlers.multitask import MultipleTasksMessageHandler
from .handlers.rpcexit import RPCExitHandler


class ExitCommand(Exception):
    pass


def signal_handler(signal, frame):
    raise ExitCommand()

signal.signal(signal.SIGINT, signal_handler)


def alive_required(func):
    """Make sure thread is running before proceeding"""
    @functools.wraps(func)
    def wrapper_alive_required(self, *args, **kwargs):
        if not self.is_alive():
            raise RuntimeError('Component has not been started. You must first run .start() method on rpc component')
        return func(self, *args, **kwargs)
    return wrapper_alive_required


class RPCComponent(threading.Thread):
    def __init__(self, cli_secret=None, rpc_cert=None, host='localhost', port=61000, log_level=logging.INFO):
        """A class providing communication with remote autobahn node. Works in separate thread
        and exposes a synchronous queue for message exchange with user application code.

        Keyword Arguments:
            cli_secret {Path} -- A path to cli_secret used to communicate with autobahn node
            rpc_cert {Path} -- A path to rpc_cert used for SSL
            host {str} -- Autobahn node hostname (default: {'localhost'})
            port {int} -- Autobahn node port (default: {61000})
            log_level {[type]} -- [description] (default: {logging.INFO})

        Raises:
            ValueError -- When cli_secret is not provided
            ValueError -- When rpc_cert is not provided
        """
        if not cli_secret:
            raise ValueError("Provide cli_secret")
        if not rpc_cert:
            raise ValueError("Provide rpc_cert")
        self.cli_secret = cli_secret
        self.rpc_cert = rpc_cert
        self.host = host
        self.port = port
        # Cross thread communication queue
        self.lock = threading.Lock()
        self.call_q = queue.Queue()
        self.response_q = queue.Queue()
        self.session = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        self.handlers = {
            'RPCCall': SingleRPCCallHandler(),
            'CreateTask': TaskRemoteFSDecorator(
                TaskRemoteFSMappingDecorator(
                    TaskMessageHandler()
                )
             ),
            'CreateMultipleTasks': MultipleTasksMessageHandler(),
            'Disconnect': RPCExitHandler(),
        }
        threading.Thread.__init__(self, daemon=True)

    @alive_required
    def post_wait(self, obj):
        """Synchronous function used for passing messages to RPC Component queue
        Arguments:
            obj {dict} -- Python dictionary of format:
            {
                "type": "message_type",
                [message specific fields]
            }
            Types: 'CreateTask', 'CreateMultipleTasks', 'RPCCall', 'Disconnect'

            Message 'Disconnect' will gracefully disconnnect rpc component from remote node
            {
                'type': 'Disconnect'
            }

            Message 'RPCCall' allows to communicate with arbitrary RPC endpoint exposed
            by remote node e.g.:
            {
                'type': 'RPCCall',
                'method_name': 'task.comp.result',
                'args': []
            }

            Message 'CreateTask' allows computing a user defined task on remote
            golem nodes. Golem task is a python dictionary containing information about
            task type, timeout, price e.g.:
            {
                'type': 'CreateTask',
                'task': {
                    'type': 'TaskType',
                    'bid': 1.0,
                    'timeout': '00:10:00',
                    'resources: []
                    ...
                    [task specific fields]
                }
            }
            For more information and default values take a look at schemas/tasks.py:TaskSchema
            class.
        Raises:
            response -- If an exception is thrown in rpc component thread then is it propagated
            through the message queue and reraised in application code.
        Returns:
            response  -- Response object
        """
        response = None
        with self.lock:
            self.call_q.put(obj)
            response = self.response_q.get()
            if isinstance(response, BaseException):
                raise response
        return response

    @alive_required
    def post(self, obj, block=True, timeout=1.0):
        with self.lock:
            self.call_q.put(obj, block=block, timeout=timeout)

    @alive_required
    def poll(self, block=True, timeout=1.0):
        response = None
        with self.lock:
            response = self.response_q.get(block=block, timeout=timeout)
            if isinstance(response, BaseException):
                raise response
        return response

    def _run(self):
        component = create_component(
            cli_secret=self.cli_secret,
            rpc_cert=self.rpc_cert,
            host=self.host,
            port=self.port
        )

        # It's a new thread, we create a new event loop for it.
        # Not doing so and using default looop might break
        # library user's code.
        loop = asyncio.new_event_loop()

        txaio.config.loop = loop
        asyncio.set_event_loop(loop)

        @component.on_join
        async def joined(session: Session, details: SessionDetails):
            self.session = session
            while True:
                try:
                    message = self.call_q.get(block=True, timeout=5.0)

                    # NOTE now if we pass context (self) to handler and it decides to
                    # send a result using context.response_q we have multiple
                    # ways to send back responses which is bad.
                    # Passing context to handlers gives flexibility but enables
                    # arbitrary side effects from handlers.

                    # Handle depending on message type
                    response = await self.handlers[message['type']](self, message)
                except queue.Empty:
                    pass
                except Exception as e:
                    self.response_q.put(e)
                else:
                    self.response_q.put(response)

        fut = asyncio.gather(
            txaio.as_future(component.start, loop)
        )
        loop.run_until_complete(fut)

    def run(self):
        # Top level exception handling layer
        # A SIGINT is sent to main thread to kill the entire process
        try:
            self._run()
        except Exception as _e:
            traceback.print_exc()
            os.kill(os.getpid(), signal.SIGINT)
